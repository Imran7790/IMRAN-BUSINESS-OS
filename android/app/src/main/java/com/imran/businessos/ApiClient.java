package com.imran.businessos;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class ApiClient {

    /*
     * Initial same-phone backend.
     * Later this can become a secure HTTPS cloud endpoint.
     */
    public static final String BASE_URL = "http://10.217.130.55:8000";

    public interface Callback {
        void success(JSONObject data);
        void error(String message);
    }

    public static void post(
            String path,
            JSONObject body,
            String token,
            Callback callback
    ) {
        new Thread(() -> {
            HttpURLConnection connection = null;

            try {
                URL url = new URL(BASE_URL + path);
                connection = (HttpURLConnection) url.openConnection();

                connection.setRequestMethod("POST");
                connection.setConnectTimeout(10000);
                connection.setReadTimeout(15000);
                connection.setDoOutput(true);
                connection.setRequestProperty(
                        "Content-Type",
                        "application/json; charset=UTF-8"
                );
                connection.setRequestProperty(
                        "Accept",
                        "application/json"
                );

                if (token != null && !token.isEmpty()) {
                    connection.setRequestProperty(
                            "Authorization",
                            "Bearer " + token
                    );
                }

                byte[] data = body.toString()
                        .getBytes(StandardCharsets.UTF_8);

                try (OutputStream out = connection.getOutputStream()) {
                    out.write(data);
                }

                int code = connection.getResponseCode();

                InputStream stream =
                        code >= 200 && code < 300
                                ? connection.getInputStream()
                                : connection.getErrorStream();

                String response = read(stream);

                JSONObject json;

                try {
                    json = new JSONObject(response);
                } catch (Exception e) {
                    json = new JSONObject();
                    json.put("detail", response);
                }

                if (code >= 200 && code < 300) {
                    callback.success(json);
                } else {
                    String message = json.optString(
                            "detail",
                            "Server request failed (" + code + ")"
                    );
                    callback.error(message);
                }

            } catch (Exception e) {
                callback.error(
                        "Cannot connect to IMRAN BUSINESS OS server. "
                        + "Make sure the backend is running."
                );
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        }).start();
    }

    private static String read(InputStream stream) throws Exception {
        if (stream == null) return "";

        StringBuilder result = new StringBuilder();

        try (BufferedReader reader =
                     new BufferedReader(
                             new InputStreamReader(
                                     stream,
                                     StandardCharsets.UTF_8))) {

            String line;

            while ((line = reader.readLine()) != null) {
                result.append(line);
            }
        }

        return result.toString();
    }
}