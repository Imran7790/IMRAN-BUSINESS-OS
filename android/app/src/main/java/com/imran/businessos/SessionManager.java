package com.imran.businessos;

import android.content.Context;
import android.content.SharedPreferences;

public class SessionManager {

    private static final String PREFS = "imran_session";
    private static final String TOKEN = "access_token";
    private static final String EMAIL = "email";
    private static final String BUSINESS_ID = "business_id";
    private static final String ROLE = "role";

    private final SharedPreferences prefs;

    public SessionManager(Context context) {
        prefs = context.getSharedPreferences(
                PREFS,
                Context.MODE_PRIVATE
        );
    }

    public void save(
            String token,
            String email,
            String businessId,
            String role
    ) {
        prefs.edit()
                .putString(TOKEN, token)
                .putString(EMAIL, email)
                .putString(BUSINESS_ID, businessId)
                .putString(ROLE, role)
                .apply();
    }

    public String token() {
        return prefs.getString(TOKEN, "");
    }

    public String email() {
        return prefs.getString(EMAIL, "");
    }

    public String businessId() {
        return prefs.getString(BUSINESS_ID, "");
    }

    public String role() {
        return prefs.getString(ROLE, "");
    }

    public boolean loggedIn() {
        return !token().isEmpty();
    }

    public void clear() {
        prefs.edit().clear().apply();
    }
}