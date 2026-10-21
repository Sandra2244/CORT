package android.net;

public class ConnectivityManager {
    public Network activa;                 // null = sin red
    public NetworkCapabilities cap;

    public Network getActiveNetwork() { return activa; }

    public NetworkCapabilities getNetworkCapabilities(Network n) {
        return n == activa ? cap : null;
    }
}
