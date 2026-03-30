"""
Terms of Service page for QuarterCharts.
Required for Google OAuth brand verification.
"""
import streamlit as st


def render_terms_page():
    """Render the terms of service page."""
    # CSS in separate call so app.py's style-hiding rule doesn't hide content
    st.markdown("""
    <style>
    .legal-content {
        max-width: 760px;
        margin: 0 auto;
        padding: 20px 16px 60px 16px;
        line-height: 1.7;
        color: #374151;
    }
    .legal-content h1 {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .legal-content h2 {
        font-size: 20px;
        font-weight: 600;
        margin-top: 28px;
        margin-bottom: 8px;
    }
    .legal-content p, .legal-content li {
        font-size: 15px;
    }
    .legal-date {
        color: #6b7280;
        font-size: 14px;
        margin-bottom: 24px;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="legal-content">
    <h1>Terms of Service</h1>
    <p class="legal-date">Last updated: March 30, 2026</p>

    <p>Welcome to QuarterCharts. By accessing or using our website at
    <a href="https://quartercharts.com">quartercharts.com</a>, you agree to
    be bound by these Terms of Service.</p>

    <h2>1. Description of Service</h2>
    <p>QuarterCharts is a financial data visualization platform that provides
    interactive charts, Sankey diagrams, and company profiles based on
    publicly available SEC EDGAR filings and market data. The service is
    designed for educational and informational purposes.</p>

    <h2>2. Account Registration</h2>
    <p>You may create an account using Google Sign-In or email and password.
    You are responsible for maintaining the confidentiality of your account
    credentials and for all activities under your account.</p>

    <h2>3. Acceptable Use</h2>
    <p>You agree not to:</p>
    <ul>
        <li>Use the service for any unlawful purpose</li>
        <li>Attempt to gain unauthorized access to our systems</li>
        <li>Scrape, crawl, or use automated tools to extract data at scale</li>
        <li>Interfere with the proper working of the service</li>
        <li>Redistribute our data or visualizations commercially without permission</li>
    </ul>

    <h2>4. Financial Disclaimer</h2>
    <p><strong>QuarterCharts is not a financial advisor.</strong> All data,
    charts, and analysis provided through our service are for educational and
    informational purposes only. They do not constitute investment advice,
    financial advice, trading advice, or any other sort of advice. You should
    not make any investment decisions based solely on information from
    QuarterCharts.</p>
    <p>Data is sourced from SEC EDGAR, Yahoo Finance, and Financial Modeling
    Prep (FMP) and may contain errors or delays. We make no guarantees about
    the accuracy, completeness, or timeliness of the data.</p>

    <h2>5. Intellectual Property</h2>
    <p>The QuarterCharts name, logo, and original content (including chart
    designs and visualizations) are the property of QuarterCharts. The
    underlying financial data is sourced from public filings and third-party
    providers.</p>

    <h2>6. Subscription and Payments</h2>
    <p>QuarterCharts offers free and paid subscription tiers. Paid
    subscriptions are billed monthly. You may cancel at any time, and your
    access will continue until the end of the current billing period.</p>

    <h2>7. Limitation of Liability</h2>
    <p>QuarterCharts is provided "as is" without warranties of any kind. We
    shall not be liable for any indirect, incidental, special, or
    consequential damages arising from your use of the service, including any
    financial losses from investment decisions.</p>

    <h2>8. Termination</h2>
    <p>We reserve the right to suspend or terminate your account if you
    violate these Terms. You may delete your account at any time by
    contacting us.</p>

    <h2>9. Changes to Terms</h2>
    <p>We may update these Terms from time to time. Continued use of the
    service after changes constitutes acceptance of the new Terms.</p>

    <h2>10. Contact</h2>
    <p>For questions about these Terms, contact us at
    <a href="mailto:sebasflores@gmail.com">sebasflores@gmail.com</a>.</p>

    </div>
    """, unsafe_allow_html=True)
