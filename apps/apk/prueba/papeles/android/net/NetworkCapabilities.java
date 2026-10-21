package android.net;

import java.util.HashSet;
import java.util.Set;

public class NetworkCapabilities {
    public static final int NET_CAPABILITY_INTERNET = 12;
    public static final int TRANSPORT_WIFI = 1;
    public static final int TRANSPORT_CELLULAR = 0;

    private final Set<Integer> puesto = new HashSet<>();

    public NetworkCapabilities con(int cap) { puesto.add(cap); return this; }

    public boolean hasCapability(int cap) { return puesto.contains(cap); }
    public boolean hasTransport(int t) { return puesto.contains(t); }
}
