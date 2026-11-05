// cort_motor.cpp — el pegamento entre Java y libllama.so
// =======================================================
// CORT en el teléfono (U1). Este archivo es lo único que sabe hablar con el motor
// GGUF; todo lo demás (qué modelo, cuánto cabe, dónde se muestra) vive en Java.
//
// Escrito contra las firmas de `include/llama.h` y `ggml/include/ggml.h` de
// llama.cpp **b12121**, bajadas y leídas el 2026-11-05 — no de memoria: la corrida
// 41971907412 costó ocho errores de javac por adivinar tres nombres de API.
//
// Reglas que respeta:
//   * Sólo API pública (llama.h / ggml.h). `common/` y `sampling.h` NO se enlazan:
//     el motor se cruzó con LLAMA_BUILD_* apagados, esas librerías no están en el APK.
//   * Un cerebro activo a la vez: el teléfono no da para dos.
//   * Nada se guarda. La pregunta entra, la respuesta sale por el callback y se
//     tira: sin archivo, sin red, sin texto en el log.
//   * Se interrumpe a mitad: `llama_set_abort_callback` lee un atomic.

#include <jni.h>
#include <android/log.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "ggml-backend.h"
#include "llama.h"

#define ETIQUETA "cort-motor"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO,  ETIQUETA, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, ETIQUETA, __VA_ARGS__)

namespace {

struct Estado {
    llama_model          * modelo   = nullptr;
    llama_context        * ctx      = nullptr;
    const llama_vocab    * vocab    = nullptr;
    llama_sampler        * muestreo = nullptr;
    std::atomic<bool>      corta{false};

    // El escucha de Java: objeto global con un método `void token(String)`.
    jobject   escucha = nullptr;
    jmethodID emite   = nullptr;

    // Lo que la pantalla puede decir con número, de la última vuelta.
    int32_t tokens    = 0;
    int64_t ms_prepar = 0;
    int64_t ms_gen    = 0;
    int32_t contexto  = 0;
};

Estado g;

void registro(ggml_log_level nivel, const char * texto, void *) {
    // llama.cpp habla por stderr y en el teléfono eso no se ve: lo que importa es
    // el aviso (WARN/ERROR), el resto se queda corto en el logcat.
    if (nivel >= GGML_LOG_LEVEL_WARN && texto) {
        LOGE("%s", texto);
    }
}

bool cortamos(void *) {
    return g.corta.load();
}

int64_t ahora_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now().time_since_epoch()).count();
}

// b12121 no exporta el decodificador UTF-8 incremental (vive en `common/unicode.h`,
// que aquí no se enlaza). Un token puede partir una vocal acentuada por la mitad y
// en la pantalla saldría un signo de interrogación. Se emite sólo hasta el último
// carácter completo: lo que falte espera al siguiente token.
size_t limite_utf8(const std::string & b) {
    size_t n = b.size();
    for (size_t i = 1; i <= 4 && i <= n; i++) {
        unsigned char c = (unsigned char) b[n - i];
        if ((c & 0x80) == 0) {
            return n;                        // ASCII: todo está completo
        }
        if ((c & 0xC0) == 0x80) {
            continue;                        // continuación 10xxxxxx, sigue buscando
        }
        int esperado = ((c & 0xE0) == 0xC0) ? 2
                       : ((c & 0xF0) == 0xE0) ? 3
                       : ((c & 0xF8) == 0xF0) ? 4 : 1;
        return i >= (size_t) esperado ? n : n - i;    // líder sin sus continuaciónes: corta antes
    }
    return n;
}

// Devuelve false si Java pidió cortar (la dueña pulsó «para») o si el callback
// levantó una excepción: en ambos casos se abandona el bucle de generación.
bool emite(JNIEnv * env, const std::string & pieza) {
    if (g.escucha == nullptr || g.emite == nullptr || pieza.empty()) {
        return true;
    }
    jstring j = env->NewStringUTF(pieza.c_str());
    if (j == nullptr) {
        return false;
    }
    env->CallVoidMethod(g.escucha, g.emite, j);
    env->DeleteLocalRef(j);
    return env->ExceptionCheck() ? (env->ExceptionClear(), false) : true;
}

void suelta_escucha(JNIEnv * env) {
    if (g.escucha) {
        env->DeleteGlobalRef(g.escucha);
        g.escucha = nullptr;
        g.emite   = nullptr;
    }
}

// Cierra lo que haya abierto. Se llama también cuando el modelo abre a medias, para
// no dejar una mitad colgada consumiendo RAM.
void cierra_todo(JNIEnv * env) {
    if (g.muestreo) { llama_sampler_free(g.muestreo);   g.muestreo = nullptr; }
    if (g.ctx)      { llama_free(g.ctx);                g.ctx      = nullptr; }
    if (g.modelo)   { llama_model_free(g.modelo);       g.modelo   = nullptr; }
    g.vocab   = nullptr;
    g.contexto = 0;
    suelta_escucha(env);
}

} // namespace

extern "C" {

// --------------------------------------------------------------------------
// ciclo de vida
// --------------------------------------------------------------------------

JNIEXPORT void JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeIniciar(JNIEnv * env, jclass) {
    llama_log_set(registro, nullptr);
    llama_backend_init();
    LOGI("backend listo · %s", llama_print_system_info());
    (void) env;
}

JNIEXPORT jstring JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeSistema(JNIEnv * env, jclass) {
    return env->NewStringUTF(llama_print_system_info());
}

// Los backends que el motor registró EN ESTE aparato, dicho con nombres. En la
// compilación de CORT sólo va el de CPU (los demás se apagaron en motor-local.yml),
// y por eso no se carga ningún plugin suelto: se lista lo que hay, sin prometer
// un acelerador que el teléfono no tiene.
JNIEXPORT jstring JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeBackends(JNIEnv * env, jclass) {
    std::string nombres;
    for (size_t i = 0; i < ggml_backend_reg_count(); i++) {
        const char * n = ggml_backend_reg_name(ggml_backend_reg_get(i));
        if (!n) {
            continue;
        }
        nombres += (nombres.empty() ? "" : ", ");
        nombres += n;
    }
    return env->NewStringUTF(nombres.c_str());
}

JNIEXPORT void JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeInterrumpe(JNIEnv * env, jclass) {
    g.corta.store(true);
    (void) env;
}

JNIEXPORT void JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeOir(JNIEnv * env, jclass, jobject escucha) {
    suelta_escucha(env);
    if (escucha == nullptr) {
        return;
    }
    g.escucha = env->NewGlobalRef(escucha);
    jclass clase = env->GetObjectClass(escucha);
    g.emite = env->GetMethodID(clase, "token", "(Ljava/lang/String;)V");
    env->DeleteLocalRef(clase);
    if (g.emite == nullptr) {
        env->ExceptionClear();
        suelta_escucha(env);
        LOGE("el escucha no tiene `void token(String)`: se responde sin streaming");
    }
}

// 0 = abierto · 1 = no leyó el archivo · 2 = no hizo contexto · 3 = sin muestreo
JNIEXPORT jint JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeAbrir(JNIEnv * env, jclass, jstring jruta,
                                                    jint contexto, jint hilos) {
    cierra_todo(env);
    const char * ruta = env->GetStringUTFChars(jruta, 0);

    llama_model_params pm = llama_model_default_params();
    pm.n_gpu_layers = 0;                     // en el teléfono no hay GPU que valga
    g.modelo = llama_model_load_from_file(ruta, pm);
    env->ReleaseStringUTFChars(jruta, ruta);
    if (!g.modelo) {
        LOGE("el archivo GGUF no abrió (ruta equivocada, truncado o RAM insuficiente)");
        return 1;
    }
    g.vocab = llama_model_get_vocab(g.modelo);

    int32_t entrenado = llama_model_n_ctx_train(g.modelo);
    int32_t n_ctx = contexto > 0 ? contexto : entrenado;
    if (n_ctx > entrenado) {
        n_ctx = entrenado;                   // prometer contexto que el modelo no
    }                                      // entrenó es mentir en la pantalla

    llama_context_params pc = llama_context_default_params();
    pc.n_ctx           = (uint32_t) n_ctx;
    pc.n_batch         = 512;
    pc.n_ubatch        = 512;
    pc.n_threads       = hilos;
    pc.n_threads_batch = hilos;
    g.ctx = llama_init_from_model(g.modelo, pc);
    if (!g.ctx) {
        cierra_todo(env);
        LOGE("sin contexto: pedía %d tokens y no hubo memoria", n_ctx);
        return 2;
    }
    llama_set_abort_callback(g.ctx, cortamos, nullptr);
    g.contexto = n_ctx;

    llama_sampler_chain_params ps = llama_sampler_chain_default_params();
    g.muestreo = llama_sampler_chain_init(ps);
    if (!g.muestreo) {
        cierra_todo(env);
        return 3;
    }
    LOGI("cerebro abierto · contexto %d de %d entrenado · %d hilos",
         n_ctx, entrenado, hilos);
    return 0;
}

JNIEXPORT void JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeCerrar(JNIEnv * env, jclass) {
    cierra_todo(env);
}

JNIEXPORT jint JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeHayCerebro(JNIEnv * env) {
    (void) env;
    return (g.modelo && g.ctx && g.muestreo) ? 1 : 0;
}

JNIEXPORT jstring JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeUltimaMedida(JNIEnv * env, jclass) {
    char cuadro[192];
    snprintf(cuadro, sizeof cuadro,
             "tokens=%d&prepar_ms=%lld&gen_ms=%lld&contexto=%d",
             g.tokens, (long long) g.ms_prepar, (long long) g.ms_gen, g.contexto);
    return env->NewStringUTF(cuadro);
}

// --------------------------------------------------------------------------
// la vuelta: preguntas y respuestas
// --------------------------------------------------------------------------

// roles[] y textos[] viajan parejos, con la última posición dejada vacía para que
// el modelo escriba él. Se devuelve nullptr si no hay cerebro abierto.
JNIEXPORT jstring JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativePreguntar(JNIEnv * env, jclass,
                                                        jobjectArray jroles,
                                                        jobjectArray jtextos,
                                                        jint max_tokens,
                                                        jfloat temperatura) {
    if (!g.ctx || !g.muestreo) {
        return env->NewStringUTF("");
    }
    const jsize n = env->GetArrayLength(jroles);
    if (n <= 0 || env->GetArrayLength(jtextos) != n) {
        return env->NewStringUTF("");
    }

    // 1. el formato de chat. b12121 trae 57 plantillas internas y ninguna es
    //    qwen2 (medido en `src/llama-chat.cpp`), así que se usa la que viene
    //    grabada dentro del propio GGUF; si no está, se escribe el diálogo plano.
    const char * plantilla = llama_model_chat_template(g.modelo, nullptr);
    std::vector<std::string> roles, textos;
    std::vector<llama_chat_message> mensajes;
    for (jsize i = 0; i < n; i++) {
        jstring jr = (jstring) env->GetObjectArrayElement(jroles, i);
        jstring jt = (jstring) env->GetObjectArrayElement(jtextos, i);
        const char * r = env->GetStringUTFChars(jr, 0);
        const char * t = jt ? env->GetStringUTFChars(jt, 0) : "";
        roles.push_back(r);
        textos.push_back(t ? t : "");
        if (jr) env->ReleaseStringUTFChars(jr, r);
        if (jt) env->ReleaseStringUTFChars(jt, t);
        env->DeleteLocalRef(jr);
        if (jt) env->DeleteLocalRef(jt);
    }
    for (size_t i = 0; i < textos.size(); i++) {
        if (!textos[i].empty()) {
            mensajes.push_back({ roles[i].c_str(), textos[i].c_str() });
        }
    }
    if (mensajes.empty()) {
        return env->NewStringUTF("");
    }

    std::string prompt;
    int32_t need = plantilla
        ? llama_chat_apply_template(plantilla, mensajes.data(), mensajes.size(), true,
                                   nullptr, 0)
        : -1;
    if (need > 0) {
        std::vector<char> b((size_t) need + 1, 0);
        if (llama_chat_apply_template(plantilla, mensajes.data(), mensajes.size(), true,
                                      b.data(), need) >= 0) {
            prompt.assign(b.data());
        }
    }
    if (prompt.empty()) {                                    // sin plantilla usable
        for (size_t i = 0; i < textos.size(); i++) {
            if (textos[i].empty()) {
                continue;
            }
            prompt += roles[i];
            prompt += "\n";
            prompt += textos[i];
            prompt += "\n";
        }
        prompt += "asistente\n";
    }

    // 2. tokens. Se mide primero con nullptr para saber cuánto cabe.
    int32_t n_tok = llama_tokenize(g.vocab, prompt.c_str(), (int32_t) prompt.size(),
                                   nullptr, 0, true, true);
    if (n_tok < 0) {
        return env->NewStringUTF("");
    }
    std::vector<llama_token> tokens((size_t) n_tok);
    if (llama_tokenize(g.vocab, prompt.c_str(), (int32_t) prompt.size(),
                       tokens.data(), n_tok, true, true) < 0) {
        return env->NewStringUTF("");
    }

    // El histórico no puede comerse la respuesta: si no cabe todo, se cortan por
    // delante los turnos viejos y se dice en la pantalla con el número real.
    int32_t reserva = max_tokens > 0 ? max_tokens : 256;
    int32_t techo = g.contexto - reserva - 8;
    if (techo < 8) {
        techo = 8;
    }
    if (n_tok > techo) {
        tokens.erase(tokens.begin(), tokens.begin() + (n_tok - techo));
    }

    // 3. cache limpia: la cara ya manda la conversación entera cada vuelta, y
    //    dejar restos dentro sumaría tokens repetidos.
    llama_memory_t memoria = llama_get_memory(g.ctx);
    if (!llama_memory_seq_rm(memoria, 0, 0, -1)) {
        llama_memory_clear(memoria, true);
    }
    llama_sampler_reset(g.muestreo);
    g.corta.store(false);
    g.tokens = 0;

    // 4. procesar el prompt por trozos del tamaño del batch.
    int32_t preparado = 0;
    const int32_t paso = 512;
    int64_t t0 = ahora_ms();
    while (preparado < (int32_t) tokens.size()) {
        int32_t cuantos = std::min(paso, (int32_t) tokens.size() - preparado);
        llama_batch lote = llama_batch_get_one(tokens.data() + preparado, cuantos);
        if (llama_decode(g.ctx, lote) != 0 || g.corta.load()) {
            g.ms_prepar = ahora_ms() - t0;
            return env->NewStringUTF(g.corta.load() ? "" : "");
        }
        preparado += cuantos;
    }
    g.ms_prepar = ahora_ms() - t0;

    // 5. palabra a palabra, con el tope de tokens y la interrupción a mano.
    std::string salida;
    std::string pendiente;
    int32_t hecho = 0;
    int64_t t1 = ahora_ms();
    while (hecho < reserva && !g.corta.load()) {
        llama_token siguiente = llama_sampler_sample(g.muestreo, g.ctx, -1);
        if (llama_vocab_is_eog(g.vocab, siguiente)) {
            break;
        }
        char pieza[32];
        int32_t l = llama_token_to_piece(g.vocab, siguiente, pieza, (int32_t) sizeof pieza,
                                         0, false);
        if (l > 0 && l <= (int32_t) sizeof pieza) {
            pendiente.append(pieza, (size_t) l);
            size_t corte = limite_utf8(pendiente);
            if (corte > 0) {
                std::string lista = pendiente.substr(0, corte);
                pendiente.erase(0, corte);
                salida += lista;
                if (!emite(env, lista)) {
                    g.corta.store(true);
                    break;
                }
            }
        }
        llama_sampler_accept(g.muestreo, siguiente);
        g.tokens++;
        hecho++;
        llama_batch uno = llama_batch_get_one(&siguiente, 1);
        if (llama_decode(g.ctx, uno) != 0) {
            break;
        }
    }
    if (!pendiente.empty()) {                    // lo último a medio formar, si acaso
        salida += pendiente;
        emite(env, pendiente);
    }
    g.ms_gen = ahora_ms() - t1;
    if (g.corta.load() && salida.empty()) {
        return env->NewStringUTF("");
    }
    return env->NewStringUTF(salida.c_str());
}

// La muestreo se arma aquí, no en Java: en el teléfono la temperatura la decide la
// tarea (0 para leer un dato, 0,7 para charlar) y el resto de los topes no cambian.
JNIEXPORT void JNICALL
Java_dev_sandra_cort_movil_CerebroLocal_nativeAjustarMuestreo(JNIEnv * env, jclass,
                                                              jfloat temperatura,
                                                              jint semilla) {
    if (!g.modelo) {
        return;
    }
    if (g.muestreo) {
        llama_sampler_free(g.muestreo);
        g.muestreo = nullptr;
    }
    llama_sampler_chain_params ps = llama_sampler_chain_default_params();
    g.muestreo = llama_sampler_chain_init(ps);
    if (temperatura <= 0.0f) {
        llama_sampler_chain_add(g.muestreo, llama_sampler_init_greedy());
    } else {
        llama_sampler_chain_add(g.muestreo, llama_sampler_init_top_k(40));
        llama_sampler_chain_add(g.muestreo, llama_sampler_init_top_p(0.9f, (size_t) 1));
        llama_sampler_chain_add(g.muestreo, llama_sampler_init_temp(temperatura));
        llama_sampler_chain_add(g.muestreo, llama_sampler_init_dist((uint32_t) semilla));
    }
    (void) env;
}

} // extern "C"
