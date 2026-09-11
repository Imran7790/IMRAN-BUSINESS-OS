package com.imran.businessos;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

public class MainActivity extends Activity {

    private SessionManager session;

    private final int BLUE = Color.rgb(21, 94, 239);
    private final int NAVY = Color.rgb(16, 24, 40);
    private final int TEXT = Color.rgb(23, 32, 51);
    private final int MUTED = Color.rgb(102, 112, 133);
    private final int BG = Color.rgb(245, 247, 251);
    private final int WHITE = Color.WHITE;
    private final int GREEN = Color.rgb(18, 183, 106);
    private final int ORANGE = Color.rgb(247, 144, 9);
    private final int PURPLE = Color.rgb(127, 86, 217);

    private int dp(int n) {
        return (int)(n *
                getResources().getDisplayMetrics().density + 0.5f);
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);

        session = new SessionManager(this);

        if (session.loggedIn()) {
            showDashboard();
        } else {
            showWelcome();
        }
    }

    private TextView text(
            String value,
            float size,
            int color,
            boolean bold
    ) {
        TextView v = new TextView(this);
        v.setText(value);
        v.setTextSize(size);
        v.setTextColor(color);

        if (bold) {
            v.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        }

        return v;
    }

    private LinearLayout column() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        return l;
    }

    private LinearLayout page() {
        LinearLayout l = column();
        l.setPadding(dp(20), dp(24), dp(20), dp(30));
        l.setBackgroundColor(BG);
        return l;
    }

    private EditText field(String hint) {
        EditText e = new EditText(this);

        e.setHint(hint);
        e.setTextSize(16);
        e.setSingleLine(true);
        e.setPadding(dp(16), 0, dp(16), 0);
        e.setBackgroundColor(WHITE);

        LinearLayout.LayoutParams p =
                new LinearLayout.LayoutParams(
                        -1,
                        dp(56)
                );

        p.setMargins(0, dp(6), 0, dp(6));
        e.setLayoutParams(p);

        return e;
    }

    private Button primaryButton(String title) {
        Button b = new Button(this);

        b.setText(title);
        b.setTextColor(WHITE);
        b.setTextSize(15);
        b.setAllCaps(false);
        b.setBackgroundColor(BLUE);

        LinearLayout.LayoutParams p =
                new LinearLayout.LayoutParams(-1, dp(54));

        p.setMargins(0, dp(8), 0, dp(8));
        b.setLayoutParams(p);

        return b;
    }

    private Button secondaryButton(String title) {
        Button b = new Button(this);

        b.setText(title);
        b.setTextColor(BLUE);
        b.setTextSize(15);
        b.setAllCaps(false);
        b.setBackgroundColor(WHITE);

        LinearLayout.LayoutParams p =
                new LinearLayout.LayoutParams(-1, dp(54));

        p.setMargins(0, dp(8), 0, dp(8));
        b.setLayoutParams(p);

        return b;
    }

    private void showWelcome() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = page();

        scroll.addView(root);

        TextView brand = text(
                "IMRAN",
                38,
                BLUE,
                true
        );

        brand.setGravity(Gravity.CENTER);

        TextView businessOs = text(
                "BUSINESS OS",
                18,
                NAVY,
                true
        );

        businessOs.setGravity(Gravity.CENTER);

        root.addView(brand);
        root.addView(businessOs);

        TextView headline = text(
                "Run your business.\nUnderstand your numbers.\nGrow with confidence.",
                28,
                NAVY,
                true
        );

        headline.setPadding(0, dp(38), 0, dp(14));
        root.addView(headline);

        TextView description = text(
                "One intelligent operating system for customers, "
                + "sales, inventory, employees, suppliers, services, "
                + "payments and business growth.",
                16,
                MUTED,
                false
        );

        description.setPadding(0, 0, 0, dp(28));
        root.addView(description);

        TextView international = text(
                "BUILT FOR MALAWI. READY FOR THE WORLD.",
                13,
                BLUE,
                true
        );

        international.setPadding(0, 0, 0, dp(20));
        root.addView(international);

        Button login = primaryButton("Sign in to your business");

        Button create = secondaryButton(
                "Create your business account"
        );

        root.addView(login);
        root.addView(create);

        TextView promise = text(
                "Your business data stays organized in one place, "
                + "so you can spend less time managing systems "
                + "and more time growing the business.",
                14,
                MUTED,
                false
        );

        promise.setPadding(0, dp(22), 0, 0);
        root.addView(promise);

        login.setOnClickListener(v -> showLogin());
        create.setOnClickListener(v -> showRegister());

        setContentView(scroll);
    }

    private void showLogin() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = page();

        scroll.addView(root);

        root.addView(text(
                "Welcome back",
                30,
                NAVY,
                true
        ));

        root.addView(text(
                "Sign in and get back to running your business.",
                15,
                MUTED,
                false
        ));

        EditText email = field("Business email");
        EditText password = field("Password");

        password.setInputType(
                InputType.TYPE_CLASS_TEXT |
                InputType.TYPE_TEXT_VARIATION_PASSWORD
        );

        root.addView(email);
        root.addView(password);

        Button login = primaryButton("Sign in");

        Button register = secondaryButton(
                "Create a new business"
        );

        root.addView(login);
        root.addView(register);

        TextView status = text(
                "",
                14,
                MUTED,
                false
        );

        status.setPadding(0, dp(12), 0, 0);
        root.addView(status);

        login.setOnClickListener(v -> {
            String emailValue =
                    email.getText().toString().trim();

            String passwordValue =
                    password.getText().toString();

            if (emailValue.isEmpty()
                    || passwordValue.isEmpty()) {

                status.setText(
                        "Enter your email and password."
                );

                return;
            }

            login.setEnabled(false);
            login.setText("Signing in...");

            try {
                JSONObject body = new JSONObject();

                body.put("email", emailValue);
                body.put("password", passwordValue);

                ApiClient.post(
                        "/api/v1/auth/login",
                        body,
                        null,
                        new ApiClient.Callback() {

                            @Override
                            public void success(JSONObject data) {
                                runOnUiThread(() -> {

                                    String token =
                                            data.optString(
                                                    "access_token"
                                            );

                                    JSONObject user =
                                            data.optJSONObject("user");

                                    String role =
                                            user == null
                                                    ? ""
                                                    : user.optString(
                                                            "role"
                                                    );

                                    String businessId =
                                            data.optString(
                                                    "business_id"
                                            );

                                    session.save(
                                            token,
                                            emailValue,
                                            businessId,
                                            role
                                    );

                                    showDashboard();
                                });
                            }

                            @Override
                            public void error(String message) {
                                runOnUiThread(() -> {
                                    login.setEnabled(true);
                                    login.setText("Sign in");
                                    status.setText(message);
                                });
                            }
                        }
                );

            } catch (Exception e) {
                login.setEnabled(true);
                login.setText("Sign in");
                status.setText(
                        "Unable to prepare the sign-in request."
                );
            }
        });

        register.setOnClickListener(v -> showRegister());

        setContentView(scroll);
    }

    private void showRegister() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = page();

        scroll.addView(root);

        root.addView(text(
                "Create your business",
                29,
                NAVY,
                true
        ));

        root.addView(text(
                "Set up your business once. "
                + "Then manage it from one operating system.",
                15,
                MUTED,
                false
        ));

        EditText name = field("Your full name");
        EditText email = field("Business email");
        EditText password = field("Password");
        EditText business = field("Business name");
        EditText category = field(
                "Business type — e.g. Retail, Solar, Law"
        );
        EditText country = field(
                "Country code — e.g. MW"
        );
        EditText currency = field(
                "Currency — e.g. MWK"
        );

        password.setInputType(
                InputType.TYPE_CLASS_TEXT |
                InputType.TYPE_TEXT_VARIATION_PASSWORD
        );

        country.setText("MW");
        currency.setText("MWK");

        root.addView(name);
        root.addView(email);
        root.addView(password);
        root.addView(business);
        root.addView(category);
        root.addView(country);
        root.addView(currency);

        Button create = primaryButton(
                "Create my business"
        );

        Button back = secondaryButton(
                "Back to sign in"
        );

        root.addView(create);
        root.addView(back);

        TextView status = text(
                "",
                14,
                MUTED,
                false
        );

        status.setPadding(0, dp(12), 0, 0);
        root.addView(status);

        create.setOnClickListener(v -> {

            if (name.getText().toString().trim().isEmpty()
                    || email.getText().toString().trim().isEmpty()
                    || password.getText().toString().isEmpty()
                    || business.getText().toString().trim().isEmpty()
                    || category.getText().toString().trim().isEmpty()) {

                status.setText(
                        "Complete the required business details."
                );

                return;
            }

            create.setEnabled(false);
            create.setText("Creating your business...");

            try {
                JSONObject body = new JSONObject();

                body.put(
                        "name",
                        name.getText().toString().trim()
                );

                body.put(
                        "email",
                        email.getText().toString().trim()
                );

                body.put(
                        "password",
                        password.getText().toString()
                );

                body.put(
                        "business_name",
                        business.getText().toString().trim()
                );

                body.put(
                        "business_category",
                        category.getText().toString().trim()
                );

                body.put(
                        "country_code",
                        country.getText().toString().trim()
                );

                body.put(
                        "currency_code",
                        currency.getText().toString().trim()
                );

                body.put(
                        "timezone",
                        "Africa/Blantyre"
                );

                body.put(
                        "language_code",
                        "en"
                );

                ApiClient.post(
                        "/api/v1/auth/register",
                        body,
                        null,
                        new ApiClient.Callback() {

                            @Override
                            public void success(JSONObject data) {
                                runOnUiThread(() -> {

                                    String token =
                                            data.optString(
                                                    "access_token"
                                            );

                                    JSONObject user =
                                            data.optJSONObject("user");

                                    String role =
                                            user == null
                                                    ? ""
                                                    : user.optString(
                                                            "role"
                                                    );

                                    String businessId =
                                            data.optString(
                                                    "business_id"
                                            );

                                    session.save(
                                            token,
                                            email.getText()
                                                    .toString()
                                                    .trim(),
                                            businessId,
                                            role
                                    );

                                    showDashboard();
                                });
                            }

                            @Override
                            public void error(String message) {
                                runOnUiThread(() -> {
                                    create.setEnabled(true);
                                    create.setText(
                                            "Create my business"
                                    );
                                    status.setText(message);
                                });
                            }
                        }
                );

            } catch (Exception e) {
                create.setEnabled(true);
                create.setText("Create my business");
                status.setText(
                        "Unable to prepare registration."
                );
            }
        });

        back.setOnClickListener(v -> showLogin());

        setContentView(scroll);
    }

    private LinearLayout card(
            String title,
            String description,
            int accent
    ) {
        LinearLayout c = column();

        c.setPadding(
                dp(16),
                dp(16),
                dp(16),
                dp(16)
        );

        c.setBackgroundColor(WHITE);

        TextView t = text(
                title,
                17,
                TEXT,
                true
        );

        TextView d = text(
                description,
                13,
                MUTED,
                false
        );

        d.setPadding(0, dp(5), 0, 0);

        c.addView(t);
        c.addView(d);

        LinearLayout.LayoutParams p =
                new LinearLayout.LayoutParams(-1, dp(112));

        p.setMargins(0, dp(6), 0, dp(6));

        c.setLayoutParams(p);

        return c;
    }

    private void showDashboard() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = page();

        scroll.addView(root);

        TextView brand = text(
                "IMRAN BUSINESS OS",
                24,
                BLUE,
                true
        );

        root.addView(brand);

        TextView welcome = text(
                "Your business command centre",
                27,
                NAVY,
                true
        );

        welcome.setPadding(0, dp(18), 0, dp(6));
        root.addView(welcome);

        TextView subtitle = text(
                "Everything important, organized in one place.",
                15,
                MUTED,
                false
        );

        root.addView(subtitle);

        LinearLayout overview = column();

        overview.setPadding(
                dp(16),
                dp(16),
                dp(16),
                dp(16)
        );

        overview.setBackgroundColor(WHITE);

        TextView overviewTitle = text(
                "BUSINESS OVERVIEW",
                13,
                BLUE,
                true
        );

        TextView overviewText = text(
                "Your sales, customers, inventory, people, "
                + "services, suppliers and finances will live here.",
                16,
                TEXT,
                true
        );

        overviewText.setPadding(0, dp(10), 0, 0);

        overview.addView(overviewTitle);
        overview.addView(overviewText);

        LinearLayout.LayoutParams overviewParams =
                new LinearLayout.LayoutParams(-1, dp(150));

        overviewParams.setMargins(0, dp(22), 0, dp(12));
        overview.setLayoutParams(overviewParams);

        root.addView(overview);

        root.addView(card(
                "Sales & Revenue",
                "Track sales, payments and business performance.",
                GREEN
        ));

        root.addView(card(
                "Customers",
                "Manage customers, relationships and history.",
                BLUE
        ));

        root.addView(card(
                "Inventory",
                "Know what you have, what is low and what to buy.",
                ORANGE
        ));

        root.addView(card(
                "Purchasing & Suppliers",
                "Manage suppliers and make smarter purchasing decisions.",
                PURPLE
        ));

        root.addView(card(
                "Employees & Services",
                "Manage your team, services, jobs and appointments.",
                BLUE
        ));

        root.addView(card(
                "Invoices & Payments",
                "Keep money owed, received and outstanding organized.",
                GREEN
        ));

        root.addView(card(
                "Business Intelligence",
                "Turn your recorded business data into useful decisions.",
                PURPLE
        ));

        root.addView(card(
                "Growth",
                "Build a stronger business from one operating system.",
                ORANGE
        ));

        Button logout = secondaryButton("Sign out");

        root.addView(logout);

        logout.setOnClickListener(v -> {
            session.clear();
            showWelcome();
        });

        setContentView(scroll);

        Toast.makeText(
                this,
                "Welcome to IMRAN BUSINESS OS",
                Toast.LENGTH_SHORT
        ).show();
    }
}