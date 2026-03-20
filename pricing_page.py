"""
Pricing / Subscription page for QuarterCharts.
Shows tiered pricing plans with feature comparison.
"""
import streamlit as st


def render_pricing_page():
    """Render the pricing page with subscription tiers."""

    st.markdown("""
    <style>
    .pricing-hero {
        text-align: center;
        padding: 40px 20px 20px;
    }
    .pricing-hero h1 {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 8px;
        font-family: Inter, system-ui, sans-serif;
    }
    .pricing-hero p {
        font-size: 1.05rem;
        color: #64748b;
        max-width: 520px;
        margin: 0 auto;
        font-family: Inter, system-ui, sans-serif;
    }
    .pricing-toggle-wrap {
        display: flex;
        justify-content: center;
        gap: 0;
        margin: 28px auto 32px;
        background: #f1f5f9;
        border-radius: 12px;
        padding: 4px;
        width: fit-content;
    }
    .pricing-toggle-btn {
        padding: 10px 28px;
        border-radius: 10px;
        font-size: 0.9rem;
        font-weight: 600;
        font-family: Inter, system-ui, sans-serif;
        cursor: pointer;
        border: none;
        transition: all 0.2s ease;
        background: transparent;
        color: #64748b;
    }
    .pricing-toggle-btn.active {
        background: #fff;
        color: #1e293b;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .pricing-card {
        background: #fff;
        border: 2px solid #e2e8f0;
        border-radius: 16px;
        padding: 28px 24px;
        text-align: center;
        transition: all 0.2s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .pricing-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    .pricing-card.popular {
        border-color: #3b82f6;
        box-shadow: 0 8px 32px rgba(59,130,246,0.15);
        position: relative;
    }
    .popular-badge {
        position: absolute;
        top: -13px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: #fff;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 4px 16px;
        border-radius: 20px;
        font-family: Inter, system-ui, sans-serif;
        letter-spacing: 0.03em;
    }
    .pricing-plan-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #475569;
        margin-bottom: 8px;
        font-family: Inter, system-ui, sans-serif;
    }
    .pricing-price {
        font-size: 2.8rem;
        font-weight: 800;
        color: #1e293b;
        font-family: Inter, system-ui, sans-serif;
        line-height: 1;
    }
    .pricing-price span {
        font-size: 1rem;
        font-weight: 500;
        color: #94a3b8;
    }
    .pricing-desc {
        font-size: 0.88rem;
        color: #64748b;
        margin: 12px 0 20px;
        font-family: Inter, system-ui, sans-serif;
    }
    .pricing-features {
        text-align: left;
        margin: 0 0 24px;
        padding: 0;
        list-style: none;
        flex: 1;
    }
    .pricing-features li {
        padding: 6px 0;
        font-size: 0.88rem;
        color: #475569;
        font-family: Inter, system-ui, sans-serif;
        display: flex;
        align-items: flex-start;
        gap: 8px;
    }
    .pricing-features li::before {
        content: '\\2713';
        color: #22c55e;
        font-weight: 700;
        flex-shrink: 0;
    }
    .pricing-cta {
        display: block;
        width: 100%;
        padding: 12px 20px;
        border-radius: 10px;
        font-size: 0.95rem;
        font-weight: 700;
        font-family: Inter, system-ui, sans-serif;
        cursor: pointer;
        transition: all 0.15s ease;
        text-align: center;
        text-decoration: none;
        margin-top: auto;
    }
    .cta-free {
        background: #f1f5f9;
        color: #475569;
        border: 2px solid #e2e8f0;
    }
    .cta-free:hover {
        background: #e2e8f0;
    }
    .cta-pro {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: #fff;
        border: none;
    }
    .cta-pro:hover {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        box-shadow: 0 4px 16px rgba(59,130,246,0.35);
    }
    .cta-enterprise {
        background: #1e293b;
        color: #fff;
        border: none;
    }
    .cta-enterprise:hover {
        background: #0f172a;
    }
    .pricing-faq {
        max-width: 640px;
        margin: 48px auto;
        padding: 0 20px;
    }
    .pricing-faq h3 {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1e293b;
        text-align: center;
        margin-bottom: 24px;
        font-family: Inter, system-ui, sans-serif;
    }
    @media (max-width: 768px) {
        .pricing-hero h1 { font-size: 1.6rem; }
        .pricing-price { font-size: 2.2rem; }
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Hero section ──
    st.markdown("""
    <div class="pricing-hero">
        <h1>Simple, transparent pricing</h1>
        <p>Start free and upgrade as you grow. No hidden fees, cancel anytime.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Billing toggle ──
    if "billing_cycle" not in st.session_state:
        st.session_state.billing_cycle = "monthly"

    toggle_cols = st.columns([1, 2, 1])
    with toggle_cols[1]:
        tc = st.columns(2)
        with tc[0]:
            if st.button("Monthly", use_container_width=True,
                         type="primary" if st.session_state.billing_cycle == "monthly" else "secondary",
                         key="billing_monthly"):
                st.session_state.billing_cycle = "monthly"
                st.rerun()
        with tc[1]:
            if st.button("Annual (Save 20%)", use_container_width=True,
                         type="primary" if st.session_state.billing_cycle == "annual" else "secondary",
                         key="billing_annual"):
                st.session_state.billing_cycle = "annual"
                st.rerun()

    is_annual = st.session_state.billing_cycle == "annual"
    pro_price = "12" if is_annual else "15"
    ent_price = "39" if is_annual else "49"
    period = "/mo" if not is_annual else "/mo"
    billed_note = "billed annually" if is_annual else "billed monthly"

    # ── Pricing cards ──
    cols = st.columns(3, gap="medium")

    with cols[0]:
        st.markdown(f"""
        <div class="pricing-card">
            <div class="pricing-plan-name">Free</div>
            <div class="pricing-price">$0<span>/mo</span></div>
            <div class="pricing-desc">Perfect for exploring financial data</div>
            <ul class="pricing-features">
                <li>5 ticker lookups per day</li>
                <li>Income statement Sankey</li>
                <li>Basic financial charts</li>
                <li>Company profile page</li>
                <li>Community support</li>
            </ul>
            <a class="pricing-cta cta-free" href="?page=login" target="_self">Get Started Free</a>
        </div>
        """, unsafe_allow_html=True)

    with cols[1]:
        st.markdown(f"""
        <div class="pricing-card popular">
            <div class="popular-badge">MOST POPULAR</div>
            <div class="pricing-plan-name">Pro</div>
            <div class="pricing-price">${pro_price}<span>{period}</span></div>
            <div class="pricing-desc">{billed_note} &middot; for serious investors</div>
            <ul class="pricing-features">
                <li>Unlimited ticker lookups</li>
                <li>Income + Balance Sankey</li>
                <li>All financial charts</li>
                <li>Quarterly & Annual data</li>
                <li>Historical trends (1Y–4Y+MAX)</li>
                <li>Analyst forecast overlay</li>
                <li>PDF export</li>
                <li>Watchlist (unlimited tickers)</li>
                <li>Priority support</li>
            </ul>
            <a class="pricing-cta cta-pro" href="?page=login" target="_self">Start Pro Trial</a>
        </div>
        """, unsafe_allow_html=True)

    with cols[2]:
        st.markdown(f"""
        <div class="pricing-card">
            <div class="pricing-plan-name">Enterprise</div>
            <div class="pricing-price">${ent_price}<span>{period}</span></div>
            <div class="pricing-desc">{billed_note} &middot; for teams & firms</div>
            <ul class="pricing-features">
                <li>Everything in Pro</li>
                <li>API access</li>
                <li>Custom data integrations</li>
                <li>Team workspaces (up to 25)</li>
                <li>White-label embedding</li>
                <li>SSO / SAML authentication</li>
                <li>Dedicated account manager</li>
                <li>Custom SLA</li>
            </ul>
            <a class="pricing-cta cta-enterprise" href="mailto:hello@quartercharts.com">Contact Sales</a>
        </div>
        """, unsafe_allow_html=True)

    # ── FAQ section ──
    st.markdown("---")
    st.markdown("### Frequently Asked Questions")

    with st.expander("Can I switch plans at any time?"):
        st.write("Yes! You can upgrade, downgrade, or cancel your subscription at any time. "
                 "Changes take effect at the start of your next billing cycle.")

    with st.expander("Is there a free trial for Pro?"):
        st.write("Yes, Pro comes with a 14-day free trial. No credit card required to start.")

    with st.expander("What payment methods do you accept?"):
        st.write("We accept all major credit cards (Visa, Mastercard, Amex) and PayPal. "
                 "Enterprise customers can also pay via invoice.")

    with st.expander("What happens to my data if I cancel?"):
        st.write("Your watchlists and settings are preserved for 90 days after cancellation. "
                 "You can export your data at any time.")

    with st.expander("Do you offer discounts for students?"):
        st.write("Yes! Students and educators get 50% off Pro with a valid .edu email address. "
                 "Contact us at hello@quartercharts.com.")
