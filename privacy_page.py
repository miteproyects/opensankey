"""
Privacy Policy page for QuarterCharts.
Required for Google OAuth brand verification.
"""
import streamlit as st
from datetime import datetime


def render_privacy_page():
    """Render the privacy policy page."""
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
    <h1>Privacy Policy</h1>
    <p class="legal-date">Last updated: March 30, 2026</p>

    <p>QuarterCharts ("we", "our", or "us") operates the website
    <a href="https://quartercharts.com">quartercharts.com</a>. This Privacy
    Policy explains how we collect, use, and protect your information when you
    use our service.</p>

    <h2>1. Information We Collect</h2>
    <p><strong>Account Information:</strong> When you sign up or sign in with
    Google, we receive your name and email address from your Google account.
    If you register with email and password, we store your email and an
    encrypted password hash (managed by Firebase Authentication).</p>
    <p><strong>Usage Data:</strong> We collect basic usage information such as
    pages visited, tickers searched, and session duration to improve our
    service.</p>
    <p><strong>Cookies:</strong> We use essential cookies for authentication
    and session management. We do not use advertising or tracking cookies.</p>

    <h2>2. How We Use Your Information</h2>
    <p>We use the information we collect to:</p>
    <ul>
        <li>Provide, maintain, and improve QuarterCharts</li>
        <li>Authenticate your identity and manage your account</li>
        <li>Save your watchlist and preferences</li>
        <li>Send service-related communications (if applicable)</li>
        <li>Detect and prevent fraud or abuse</li>
    </ul>

    <h2>3. Data Sharing</h2>
    <p>We do not sell, rent, or share your personal information with third
    parties for marketing purposes. We may share data with:</p>
    <ul>
        <li><strong>Firebase/Google:</strong> For authentication services</li>
        <li><strong>Hosting providers:</strong> To operate our infrastructure</li>
        <li><strong>Law enforcement:</strong> If required by law</li>
    </ul>

    <h2>4. Data Security</h2>
    <p>We implement industry-standard security measures including encrypted
    connections (HTTPS), secure authentication tokens, rate limiting, and
    security headers to protect your data.</p>

    <h2>5. Data Retention</h2>
    <p>We retain your account information as long as your account is active.
    You may request deletion of your account and associated data by contacting
    us at the email below.</p>

    <h2>6. Your Rights</h2>
    <p>You have the right to access, correct, or delete your personal data.
    You may also withdraw consent for data processing at any time by deleting
    your account.</p>

    <h2>7. Children's Privacy</h2>
    <p>QuarterCharts is not intended for children under 13. We do not
    knowingly collect personal information from children.</p>

    <h2>8. Changes to This Policy</h2>
    <p>We may update this Privacy Policy from time to time. We will notify
    you of any changes by posting the new policy on this page with an updated
    date.</p>

    <h2>9. Contact Us</h2>
    <p>If you have questions about this Privacy Policy, please contact us at
    <a href="mailto:sebasflores@gmail.com">sebasflores@gmail.com</a>.</p>

    </div>
    """, unsafe_allow_html=True)
