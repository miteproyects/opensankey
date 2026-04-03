"""
Pricing / Subscription page for QuarterCharts.
Shows tiered pricing plans with feature comparison.
Plans are loaded dynamically from the database (managed via NSFE Pricing tab).
"""
import json
import streamlit as st


def render_pricing_page():
    """Render the pricing page with subscription tiers from database."""

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
    .pricing-card {
        background: #fff;
        border: 2px solid #e2e8f0;
        border-radius: 16px;
        padding: 32px 24px 28px;
        text-align: center;
        transition: all 0.2s ease;
        display: flex;
        flex-direction: column;
        margin-top: 20px;
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
        padding-top: 36px;
    }
    .popular-badge {
        position: absolute;
        top: -14px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: #fff;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 5px 18px;
        border-radius: 20px;
        font-family: Inter, system-ui, sans-serif;
        letter-spacing: 0.03em;
        white-space: nowrap;
        z-index: 2;
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
        margin: 12px 0 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid #e2e8f0;
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
        padding: 8px 0;
        font-size: 0.88rem;
        color: #475569;
        font-family: Inter, system-ui, sans-serif;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        line-height: 1.4;
        border-bottom: 1px solid #f1f5f9;
    }
    .pricing-features li:last-child {
        border-bottom: none;
    }
    .pricing-features li::before {
        content: '\\2713';
        color: #22c55e;
        font-weight: 700;
        flex-shrink: 0;
        margin-top: 1px;
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
    .cta-default {
        background: #f1f5f9;
        color: #475569;
        border: 2px solid #e2e8f0;
    }
    .cta-default:hover {
        background: #e2e8f0;
    }
    .cta-popular {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: #fff;
        border: none;
    }
    .cta-popular:hover {
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

    # ── Load plans from database ──
    try:
        from database import get_all_plans, ensure_no_login_plan
        ensure_no_login_plan()
        plans = get_all_plans(active_only=True)
    except Exception:
        plans = []

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

    # ── Pricing cards (dynamic from DB) ──
    if not plans:
        # Fallback if DB is unavailable
        st.warning("Pricing information is currently unavailable. Please try again later.")
        return

    num_plans = len(plans)
    cols = st.columns(min(num_plans, 4), gap="medium")

    for idx, plan in enumerate(plans):
        with cols[idx % len(cols)]:
            # Parse features
            features = plan.get("features", [])
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except Exception:
                    features = []

            # Price display
            price_monthly = float(plan.get("price_monthly", 0))
            price_annual = float(plan.get("price_annual", 0))

            if is_annual and price_annual > 0:
                display_price = f"{price_annual:.0f}"
                billed_note = "billed annually"
            else:
                display_price = f"{price_monthly:.0f}"
                billed_note = "billed monthly" if price_monthly > 0 else ""

            is_popular = plan.get("is_popular", False)
            plan_name = plan.get("name", "Plan")
            description = plan.get("description", "")
            cta_text = plan.get("cta_text", "Get Started")
            cta_url = plan.get("cta_url", "") or "?page=login"
            slug = plan.get("slug", "")

            # Determine CTA style based on plan characteristics
            if is_popular:
                card_class = "pricing-card popular"
                cta_class = "cta-popular"
            elif slug == "enterprise" or price_monthly >= 40:
                card_class = "pricing-card"
                cta_class = "cta-enterprise"
            else:
                card_class = "pricing-card"
                cta_class = "cta-default"

            # Build features HTML
            features_html = ""
            for feat in features:
                features_html += f"<li>{feat}</li>"

            # Description with billing note
            if billed_note and price_monthly > 0:
                desc_html = f"{billed_note} &middot; {description}" if description else billed_note
            else:
                desc_html = description

            # Build card HTML
            popular_badge = '<div class="popular-badge">MOST POPULAR</div>' if is_popular else ""

            card_html = f'<div class="{card_class}">{popular_badge}<div class="pricing-plan-name">{plan_name}</div><div class="pricing-price">${display_price}<span>/mo</span></div><div class="pricing-desc">{desc_html}</div><ul class="pricing-features">{features_html}</ul><a class="pricing-cta {cta_class}" href="{cta_url}" target="_self">{cta_text}</a></div>'
            st.markdown(card_html, unsafe_allow_html=True)

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
