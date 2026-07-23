// ParkSafe Municipal Service (Java)
// ---------------------------------
// A small, dependency-free REST microservice for the Municipal Admin side of
// ParkSafe: it owns the tow-zone registry and issued challans (tickets).
// Built purely on the JDK's com.sun.net.httpserver so it compiles and runs
// with nothing but `javac` / `java` — no Maven/Gradle/Spring needed.
//
// Endpoints:
//   GET  /health
//   GET  /tow-zones
//   POST /tow-zones           body: {"area":"...","lat":..,"lng":..,"radiusM":..,"reason":"..."}
//   GET  /challans
//   GET  /challans?plate=DL01AB1234
//   POST /challans            body: {"spotId":.., "plate":"..", "area":"..", "amount":.., "reason":".."}
//
// Build:  javac ChallanService.java
// Run:    java ChallanService [port]   (default port 8081)

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantLock;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ChallanService {

    // ---------- domain models ----------

    static class TowZone {
        long id;
        String area;
        double lat, lng;
        double radiusM;
        String reason;
        String createdAt;
    }

    static class Challan {
        long id;
        long spotId;
        String plate;
        String area;
        double amount;
        String reason;
        String status = "UNPAID";
        String issuedAt;
    }

    // ---------- in-memory store (thread-safe) ----------

    static final List<TowZone> towZones = new ArrayList<>();
    static final List<Challan> challans = new ArrayList<>();
    static final AtomicLong towZoneSeq = new AtomicLong(1);
    static final AtomicLong challanSeq = new AtomicLong(1);
    static final ReentrantLock lock = new ReentrantLock();

    static void seedDemoData() {
        TowZone z = new TowZone();
        z.id = towZoneSeq.getAndIncrement();
        z.area = "Janpath Market Lot";
        z.lat = 28.6270; z.lng = 77.2190; z.radiusM = 60;
        z.reason = "No-parking arterial road; frequent Municipal Corp drives";
        z.createdAt = Instant.now().toString();
        towZones.add(z);

        TowZone z2 = new TowZone();
        z2.id = towZoneSeq.getAndIncrement();
        z2.area = "Sunder Nagar Driveway";
        z2.lat = 28.6030; z2.lng = 77.2420; z2.radiusM = 40;
        z2.reason = "Private driveway repeatedly reported as illegal parking";
        z2.createdAt = Instant.now().toString();
        towZones.add(z2);
    }

    public static void main(String[] args) throws IOException {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 8081;
        seedDemoData();

        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/health", ChallanService::handleHealth);
        server.createContext("/tow-zones", ChallanService::handleTowZones);
        server.createContext("/challans", ChallanService::handleChallans);
        server.setExecutor(null);
        server.start();
        System.out.println("ParkSafe Municipal Service (Java) listening on port " + port);
    }

    // ---------- handlers ----------

    static void handleHealth(HttpExchange ex) throws IOException {
        writeJson(ex, 200, "{\"status\":\"ok\",\"service\":\"parksafe-municipal-java\"}");
    }

    static void handleTowZones(HttpExchange ex) throws IOException {
        withCors(ex);
        if ("OPTIONS".equals(ex.getRequestMethod())) { writeJson(ex, 204, ""); return; }

        if ("GET".equalsIgnoreCase(ex.getRequestMethod())) {
            StringBuilder sb = new StringBuilder("[");
            lock.lock();
            try {
                for (int i = 0; i < towZones.size(); i++) {
                    TowZone z = towZones.get(i);
                    if (i > 0) sb.append(",");
                    sb.append("{\"id\":").append(z.id)
                      .append(",\"area\":").append(q(z.area))
                      .append(",\"lat\":").append(z.lat)
                      .append(",\"lng\":").append(z.lng)
                      .append(",\"radiusM\":").append(z.radiusM)
                      .append(",\"reason\":").append(q(z.reason))
                      .append(",\"createdAt\":").append(q(z.createdAt))
                      .append("}");
                }
            } finally { lock.unlock(); }
            sb.append("]");
            writeJson(ex, 200, sb.toString());
        } else if ("POST".equalsIgnoreCase(ex.getRequestMethod())) {
            Map<String, String> body = parseFlatJson(readBody(ex));
            TowZone z = new TowZone();
            lock.lock();
            try {
                z.id = towZoneSeq.getAndIncrement();
                z.area = body.getOrDefault("area", "Unknown area");
                z.lat = parseDoubleOr(body.get("lat"), 0);
                z.lng = parseDoubleOr(body.get("lng"), 0);
                z.radiusM = parseDoubleOr(body.get("radiusM"), 50);
                z.reason = body.getOrDefault("reason", "Reported by municipal admin");
                z.createdAt = Instant.now().toString();
                towZones.add(z);
            } finally { lock.unlock(); }
            writeJson(ex, 201, "{\"id\":" + z.id + ",\"status\":\"created\"}");
        } else {
            writeJson(ex, 405, "{\"error\":\"method_not_allowed\"}");
        }
    }

    static void handleChallans(HttpExchange ex) throws IOException {
        withCors(ex);
        if ("OPTIONS".equals(ex.getRequestMethod())) { writeJson(ex, 204, ""); return; }

        if ("GET".equalsIgnoreCase(ex.getRequestMethod())) {
            String query = ex.getRequestURI().getRawQuery();
            String plateFilter = null;
            if (query != null) {
                for (String kv : query.split("&")) {
                    String[] parts = kv.split("=", 2);
                    if (parts.length == 2 && parts[0].equals("plate")) plateFilter = parts[1].toUpperCase();
                }
            }
            StringBuilder sb = new StringBuilder("[");
            lock.lock();
            try {
                boolean first = true;
                for (Challan c : challans) {
                    if (plateFilter != null && !c.plate.toUpperCase().equals(plateFilter)) continue;
                    if (!first) sb.append(",");
                    first = false;
                    sb.append("{\"id\":").append(c.id)
                      .append(",\"spotId\":").append(c.spotId)
                      .append(",\"plate\":").append(q(c.plate))
                      .append(",\"area\":").append(q(c.area))
                      .append(",\"amount\":").append(c.amount)
                      .append(",\"reason\":").append(q(c.reason))
                      .append(",\"status\":").append(q(c.status))
                      .append(",\"issuedAt\":").append(q(c.issuedAt))
                      .append("}");
                }
            } finally { lock.unlock(); }
            sb.append("]");
            writeJson(ex, 200, sb.toString());
        } else if ("POST".equalsIgnoreCase(ex.getRequestMethod())) {
            Map<String, String> body = parseFlatJson(readBody(ex));
            Challan c = new Challan();
            lock.lock();
            try {
                c.id = challanSeq.getAndIncrement();
                c.spotId = (long) parseDoubleOr(body.get("spotId"), 0);
                c.plate = body.getOrDefault("plate", "UNKNOWN");
                c.area = body.getOrDefault("area", "Unknown area");
                c.amount = parseDoubleOr(body.get("amount"), 500);
                c.reason = body.getOrDefault("reason", "Parked in a tow-risk / illegal zone");
                c.issuedAt = Instant.now().toString();
                challans.add(c);
            } finally { lock.unlock(); }
            writeJson(ex, 201, "{\"id\":" + c.id + ",\"status\":\"issued\",\"amount\":" + c.amount + "}");
        } else {
            writeJson(ex, 405, "{\"error\":\"method_not_allowed\"}");
        }
    }

    // ---------- tiny helpers (no external JSON lib needed) ----------

    static void withCors(HttpExchange ex) {
        ex.getResponseHeaders().add("Access-Control-Allow-Origin", "*");
        ex.getResponseHeaders().add("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
        ex.getResponseHeaders().add("Access-Control-Allow-Headers", "Content-Type");
    }

    static String readBody(HttpExchange ex) throws IOException {
        InputStream is = ex.getRequestBody();
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[1024];
        int n;
        while ((n = is.read(buf)) != -1) bos.write(buf, 0, n);
        return bos.toString(StandardCharsets.UTF_8);
    }

    static void writeJson(HttpExchange ex, int status, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().add("Content-Type", "application/json");
        ex.sendResponseHeaders(status, bytes.length == 0 ? -1 : bytes.length);
        if (bytes.length > 0) {
            try (OutputStream os = ex.getResponseBody()) { os.write(bytes); }
        } else {
            ex.getResponseBody().close();
        }
    }

    static String q(String s) {
        if (s == null) return "null";
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    static double parseDoubleOr(String s, double fallback) {
        if (s == null || s.isEmpty()) return fallback;
        try { return Double.parseDouble(s); } catch (NumberFormatException e) { return fallback; }
    }

    // Minimal flat-JSON-object parser: handles {"k":"v","k2":1.5,...}
    // Sufficient for the simple request bodies this service accepts —
    // not a general-purpose JSON parser.
    static Map<String, String> parseFlatJson(String body) {
        Map<String, String> out = new java.util.LinkedHashMap<>();
        if (body == null) return out;
        Pattern p = Pattern.compile("\"([^\"]+)\"\\s*:\\s*(\"([^\"]*)\"|[-0-9.eE]+)");
        Matcher m = p.matcher(body);
        while (m.find()) {
            String key = m.group(1);
            String val = m.group(3) != null ? m.group(3) : m.group(2);
            out.put(key, val);
        }
        return out;
    }
}
