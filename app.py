"""
Quarter Charts Ã¢ÂÂ A local financial charting app.

Run with:  streamlit run app.py
"""

import os
import sys

# ── Patch Streamlit index.html to add Google site verification in <head> ──
def _patch_streamlit_head():
    """Inject meta tags into Streamlit's index.html <head> at import time."""
    try:
        import streamlit as _st
        idx = os.path.join(os.path.dirname(_st.__file__), "static", "index.html")
        if os.path.isfile(idx):
            with open(idx, "r") as f:
                html = f.read()
            changed = False
            # Google site verification
            tag = '<meta name="google-site-verification" content="4yRIohYFN8d_gMq4yQUG3sF9n_tbeZqKEL4pp-SlK9A" />'
            if "google-site-verification" not in html:
                html = html.replace("<head>", f"<head>{tag}", 1)
                changed = True
            # Fix title to match OAuth app name
            if "<title>Streamlit</title>" in html:
                html = html.replace(
                    "<title>Streamlit</title>",
                    "<title>QuarterCharts \u2014 Financial Data Visualization</title>",
                )
                changed = True
            # Add meta description for Google crawlers
            if 'name="description"' not in html:
                desc = '<meta name="description" content="QuarterCharts is a financial data visualization platform that turns SEC filings into interactive Sankey diagrams, quarterly income charts, and company profiles." />'
                html = html.replace("</head>", f"{desc}</head>", 1)
                changed = True
            # Replace noscript with content Google's bot can parse for OAuth verification
            _noscript_content = (
                '<noscript>'
                '<div style="max-width:760px;margin:40px auto;font-family:sans-serif;color:#333">'
                '<h1>QuarterCharts &mdash; Financial Data Visualization</h1>'
                '<p>QuarterCharts is a financial data visualization platform that turns '
                'SEC filings into interactive Sankey diagrams, quarterly income charts, '
                'and company profiles &mdash; all from one search. Built for investors '
                'who value clarity over clutter.</p>'
                '<p>You need to enable JavaScript to run this app.</p>'
                '<p><a href="/?page=privacy">Privacy Policy</a> | '
                '<a href="/?page=terms">Terms of Service</a></p>'
                '</div>'
                '</noscript>'
            )
            if "Privacy Policy" not in html and "<noscript>" in html:
                import re as _re
                html = _re.sub(
                    r'<noscript>.*?</noscript>',
                    _noscript_content,
                    html,
                    flags=_re.DOTALL,
                )
                changed = True
            if changed:
                with open(idx, "w") as f:
                    f.write(html)
    except Exception:
        pass

_patch_streamlit_head()

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any
import base64
from PIL import Image
from io import BytesIO

# ── Security Headers (must run before any response is served) ──
from security_headers import inject_security_headers, get_https_redirect_meta
inject_security_headers()

# ── Auth module ──
from auth import restore_session, get_auth_params, clear_session_state

from data_fetcher import (
    get_company_info,
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_analyst_forecast,
    validate_ticker,
    format_large_number,
    compute_margins,
    compute_eps,
    compute_revenue_yoy,
    compute_per_share,
    compute_qoq_revenue,
    compute_expense_ratios,
    compute_ebitda,
    compute_effective_tax_rate,
    get_revenue_by_product,
    get_revenue_by_geography,
    _opensankey_get_segments,
)
from info_data import get_company_icon

# ─── Database module ───────────────────────────────────────────────────────
from database import initialize_schema, is_db_ready

# Lazy-load page modules: only import when their page is active (saves ~2s)
# from profile_page import render_profile_page   Ã¢ÂÂ imported in page routing
# from earnings_page import render_earnings_page  Ã¢ÂÂ imported in page routing
# from watchlist_page import render_watchlist_page Ã¢ÂÂ imported in page routing
from charts import (
    COLORS,
    create_income_chart,
    create_margins_chart,
    create_eps_chart,
    create_revenue_yoy_chart,
    create_opex_chart,
    create_ebitda_chart,
    create_tax_chart,
    create_per_share_chart,
    create_qoq_revenue_chart,
    create_sbc_chart,
    create_shares_chart,
    create_expense_ratios_chart,
    create_effective_tax_rate_chart,
    create_cash_flow_chart,
    create_cash_position_chart,
    create_capex_chart,
    create_assets_chart,
    create_liabilities_chart,
    create_equity_debt_chart,
    create_pe_chart,
    create_market_cap_chart,
    create_analyst_forecast_chart,
    create_revenue_by_product_chart,
    create_revenue_by_geography_chart,
    create_income_breakdown_chart,
)


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

# Logo and favicon as base64
FAVICON_B64 = "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"

LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAQAElEQVR4AexcCZRcxXV99btnn9ZoYQRiEYKwKKwWiARhbHVzEss+wQuJkbENnMjGJg4hjvDKAdI9dgj2AYwXDLEJUoh9YlsigCOEl2OfaR8nBmxAgAEJI0CIZSQLJM3WM9Pdv17urd+/p2fp7plRDyPOmebfeq9evap69d6r+v/3tPBk9jOjHpgNwIy6X2Q2ALMBmGEPzPD0sztgNgAz7IEZnn52B8wGYIY9MMPTz+6A2QDMsAdmePqDcgecfW9v/OyNRH/q7I0B/nxjpvMsYPmGvs7lP+hPLf9Bb+oMYEr+O4g6HRQBOPfegfjb7810vv3egc5z7ulXo16neICRpIokLaCqcXEwcXFyLylCHETenIIpMxaAc5Hl5/4PnH5fplPFdtLBVm3cqojC40rqoELeogjkKo5nHZjCmg+qLm96AOKbBuLv2DTQaZjhVoKslkofU2gsUCU1otgG4iBv6c+bFoD4pt74yk2ZTt/aTrU2zuRVuFHhPseDGZ9Cy7WVUifAzgBF/7fyNe0BYMavRMZbiXTCwXFxWVvIYGazCj7MapDSC3JcCFHYVkoL/d1YpZ1qw1/04GBnbUaqPsq0BiC+qT9l3flu44rD3SICBHmc+S6DIXJnOprFnfFgKAvacT9AxelDzr5E0IYdAVn1JU5O4+8e7k9lsjb+gV8PIFkm13cq2tMSAGZ9/P4B3FxNUpjlxUwtyWKmt4z3YXZTXqLr+rNOlLaRry16crAZQ8K8JMi0XzUPALMez5E4bpD1zN4iRILMLVAsDU2QsV4KZDZWP0IXikF9dBsGqeH1yQf7U+E81mr8A78aSNVw+HGHqmkAztvcnxITZhCztRScn/UCpZPBgqAsvQIdFS8tYogO7KIOI6YD9Q6jChjUJa2GOlKTz2X/B9vVJHuy6pJCYJjF+8Z0H0VeTazHIPH7M50WC3AZZLmIYfDchkjcWY6FOR1HRRxvQUXT1rcJtTbxyIdazKMXNSeIxz7cknrsowEeB338kljq8UtaUk9c0pr4/SXNCUxdk0utJruzNrBHNaAwGmyyJhOUGaQmAUg8MMCnhjh8isQxmKoUqArrpACUcIHhZdKeaOK3q1vM7y5sTTzy4ViakDf587Ff96bclDSsFBAieab1hnzAAYjj2EH2xF0mw/iAapBBSB9cBV5AQ5i0qE08/MHmxEMXxnDMYKUzeVlJ0u5gB9DGgv3cAYRKcrrMO6AAuDMfx05gnAmIy3bwCjieYvKgPLOn4Hg4x3zzOW349lPaun6Lzr1rqy5Y95i23/6ELrz9id6F6x7rbb/14Z4FG57Xtv98Qlu++YA2sA9mrHp9rLM7RaUhHyUTCERIAbIEd8H7pumGPOUAMPMtnI+FFp7jVbATAiDth+USyHzpePCvmyac8ehvvvOINv/70zr/1i2ZRQ3dvTG/T7ys35Vt8qV3Z7fsW3CavLHgtNY3dna37lvYEuuVesnmGsRrPlpa/uN3/Yfe9qTO2/CyNnEsOnI0/vaX3Skf2Y8nHhnMW7cOtaAWa8EaKFfyhNrkdNyQpxSAsZnPDA/BZZInDaC4sT50YUsqqFUuN6hGvv+czvnuo5nDItmexp5uGbhyWXPX5cvnvP6PZ5uey5cfnll9ismmEia/2hifcDxkq48yAx9fanovO9nsXXNWy+6mmAz0vy4N33tS2u/8X41t2KCR0tlx70+6OrI93AHM/lDmKAu0OzINR9GUAmCZ+bAUSSLIrlGQQp0UwJPNRM/5O7dpbPcWOZSLnfdC8x8vO6dt71XnmAExpuACtkwQ6LPmGDO4ZpnZ3/isvCHyunT/af8h337qj60c4eKf7Uu5N29UuIbBnC2xWwPeghJKKmKtjZ/fOVDTN+RJB4BHD2wW0TDLSUuBJmEd1HgTOnJ4vvM8H8p2Rw9dJrsvPt70rF5teCq7qQ604FgfP7e9t21ry+ttDe3eXVt7FoiYpPCD0PbkUBR4Ere20SI2QGbwbkC2VphUAPgVA7ImyYwhcHMSQpklBDMFRro2Zv4FTelqhvLG6ndn5g/0S+/fnzZ3H4+Uan2m2s5AMLi/eCm/FikutNvSbpxFjsL+gFq3LsejvUjRrmrj7+vsT03VhtH9JhUAJDayhtldCg7J+jBVYyeU+bds2Tc3OiiNR5zZ/Ed31HCIacZHNr+Rgk+vQZ4UZ+LjJyvwrwgaQkrZCKDNteNt/wM1OoomHAD3HQ/+JKiwbiRgs5MFFAZ2PHRB9Wf72369f15sYK53+XLz+nRm/QgHooIdmwztF9jdM2SFO8EB9aAtWEtRhogFfEEOPd9oEsMd8DXhAKjxVgazMdtLQSnroCodv/mb6k87zPz6SJu57ByzF73etOuiTXvc0aFhJnNm8qREyJMSpbIC78QoEKj4RHYBu1XChALgsh9PAJhUCGSROyNdVvD8xIpwyUSczzO/2Z8bnarzUyn18H5Qxxv3+he1kSBPGdsqLRY2Jp3NYLgO8vsHfSF1gNyd92qL63N17ABSCzn1yLN/XvSAd8GEAhAsillOsDaaiqhIB1sqgY7KDmZi886UfZX0RrelVL2v/Uab+H7Q9v79c/KN0tDQ3VV8pj+sUbx8756GRefvi/FRdn2nNrJP6TgX3bsnjnpajKRFCZPO5CVdHzHSADjqgQeUT3hYEC7hR0PGfTsraaw+LSKEnN/Zy3Flqh+vWkf+LdeqJBnxAHA2LMIlw3XpeGgCR09dRto027x/wme+qqHjF/5e2lrqxWx/RTJrl83bf8Uppo8vZGv4nA/wBeyKxELI5nfHTpRMS4OYkx6V2PrOFxsFY3CNP7ygPf2j97UnfvTe9sQP33tI4gfnz080Gr+jvclIe2OAQ0CJenjFrQ0LZ8aH/E/fFUv85C9jic1/0ZrYfF5r4v5EM1D9fsf5ywFTlWsK5FY8RBgxR+qoA+TMEBBBXSb4YWaq6c5N9GmHR8p3Ht03h47/1KmyHzfrTCph8tWmW82343PMwIVnSk9LwxKz4Wlp6VSNlu2nSKiwEbxjSQlXmd7CqzY8EmilywBVJBMBg8kXzn4kiVTLfn69kMlI7JBtbT3V5mN7CpmbiUiLyLwMHW/wVkv5ZMA+qxGI9j0y2POsNG14SuvH6+8yHItwVOB18lwfQb4E4/U/UFnVAMDrcS1mOnfCyCmNStWzP7tdWubFpI8vQiN7j63R+YtiSxq63yb43sfkxmpMTpLArtlyovSjV325IKAtuDQgjAP87yolIlevdVExAO/8cX9KYUGwAwqZ7+rkA1T7kg19TX93pqV+i3NCRft57LTNXdLYdab0pozBHquoPuFGjvXMyZLpjUpDZ+fI4wj2ict+zMa1WhROVkLdUw92woQnnIRixQAMj1P4pULx7A9bTDrkytHvPipNkWx+qGr2Kwff19zsSz8dVm68qco55rFdMpCdLw1IHePGKbmjIK+ciIWyAoSUsulCxQBYNStpRJARMBsVPArjGVkA3g/0V9UMizRJY4/0DFTT+9qD0igyL4cz/4CPnXJz8Th6ba/4Dzy33d0P6H+ux63P/R3ABruB6yQs1liCcuMeiLxiAJAEcUB4Jo6dBEmEbTtWPizBwszAUKbxqhVHDg5Lx3IpVa+xVRo/eaZUDdTY3mMlF6QzK97zy/515z3Qv+7ce/rXLf9R37rT7+pbd+Idfeuuf3ZgWc4/rj6V0lFrx3oUY5UC1fCiOORrSUcZMTw0f70MB4pi5nL47YdaUsM9xnLf2i719dbPisGtemxzUTLnQbwLZWWITy5F4QEweSNHWWtWKYDvtFeRz6ussoCfzx5VF5HsSR8U92jq1shEwiJxYb06DHTAJcE9Ao44AJvKdS0bACk+/xe6TmH+yJDUDeVj2cIIZcnCdqnr6pWqemUHGKdB1eCYxOYFVdiuBSqISN8WyTfNRwDcGTSyM1TRCZdj0AaKC8z0XGUDYJEVLjswuxbAbLCoKNtEq96Am3MSbYh2cZllrU+l1NvTt99L4XGxrNIkG3w4mU8uXIPvq5CyTrkgAnwgGNi7x/O8vKE8AJ2uLMRyjQDlis6KhROTNGNC6mUD4HrDnrHnv3FNIpW7UslrlMi8xkUVA7DofInU182tqMOxJgv4T0bDCYIoiLS1+541IxcRrjekblLjyukqRhpQMguS3Pne2YJieDHq1qHIjBL1cVl/QLxn9giHGredwqE28aKDXRV1qDcZ0MeWuwB200xFBgfUCts4VuugWGsENycVtjtAn+vENpBg96MNArfjMQb71RplA+AmgkGMAomru8IEpZqqj6BDEXwpFucIrsu4RSwqpn7BopoGgBPRX/AdHCli1Tgq9CSOILb3DdGuqLBkfQS44AI4BttYJa01ygcALuHkQSYIFoFssAHcGSm6sroxfdVVpqBx6nVPrjj1S1tXLLtxx4o/u+WVFef82+4VK+/qWREOxSzn+W3d+a/iw27eC9RiUWwMFQXf6KONa3RrAs9+Yd3xTmYRu+kJQfkAFIxUCTJeHCUfwE7gHtCAv3U8k3YdpdynFz5oiVbWKe279LMPf8T37d1G9W5j83ersXfjkLtb/fzd532/5wLq4vQRRdZbgFQVUgcW4HG1NmBOKoIPpaFeSNE07VfZADBZAkOQ9bCQWTESyKYq5mVyak9qrxyphm6xe7bviVQZqtic921eccAzmx18ZqcVC5rP2zqnCMcyo61Vl/08eULd8CbQhKAjPlDD4qCnBM6jkWvk2gEsle1u7BoXZQPgeTYN02ASM56zkpZADf5OQHl5LDwklpc2qejcrvvFj8baK+qMnoHOsIrtZa2oA3iXLYEm/C8K76pbwPD5bxiJQEVe7tkd8XN4PaNOQVYklJWi2FB7pmwA8ngw5AIUhTI7AKSLEE4GeTVzBvsk39uPF54KiqmUsdFWsfybQQW14Sac4RZOt/wtJ4G6j7rm4XbwThGsdee/uB2ADSNKHTA+dGC/1zj/UAwDDutQrA0Lg44KJMOA3AJsJ3Vj17goG4DheQzYUqCK45Pl277XW7ILKBmJ/a9KHokaHAsjm0bUvC7JyYPiviAb0TBOxTkQjqTDhBkNBwqcTSfBt64H/B80I4vZDB+KkCFwnDwtSIrup6kmUHF9HEWBC7q4HOOaijpBrbalV244/kMJ2jsiIyDAhbUwU2CkmGS5/pRf+R7JRvr769GBEaRoXLwUx9cQ9VKPuSrquc7wsuK8twgCg2G5C8CzLmgLdESQ8LgviLgYocI+CurZnHn1Sam78OSTc9jkUlwPo8QKaLDLRQKKtUKmgBu7xkXZAATzmLS4bDciRSoiyrrg4aNyd4Mv4eobW4bW75AG9Cp7pYyx/b07hja6r6TLqrkGpq1zBhyCgInAwwrHClF4xnc6yGCoCH0q2IYCPUGlLmoi3RHJ0TY3IPRwhayjQoED1kkaSKelrOhB9f1fKVbBTCC4YKwB62BWcO02fsr6ysdQ3TwZlP3SKFU+a+JLgEAE7AAADJBJREFUhr6yvW/Fsbf3rF9yW8+60Tj61sJzPrLcL2S84ty32A0K5+PRFBuArhdQQTw0gDueeLPGjdr3jZfPR/jzdmcOtoBbE46lgKoo1ut4BEwxrrJegOtT46JiADxPsAMEH2QCyvCaTFJceKQMRjypH/3b/HCsIjVG9+ftofiC5t02qsQqW6erwK8i1Xp7lNOlj+kQOh7ZYJHdWnBUYQMgAiKKXUpYUFTEWIsZVIZUcm6csBhvMZApQJUCcZuC9VqjYgBG3ge4qHEgkqxkFLd6rvf1gd7DX2+upMe2IaS0H/HVRvLG5zeVni9+iAg9D9/6vliATnfZz3sAg2HzyPyCDgazyHw+uVAPDUbhUUU/m4Uy2sMLYkGyB0Bl5E4XYb9gnDAUYc/a0IoB4BSYFrvAkIU1oBCwUiCiYqoeQ7HXDsnYtqbmqrsAbwP5qCIAQNQaG7HGj1rRiBUEhtMCcLK17ngReE7hNLEKVoM2lEIVZD6bEC0DI0XQR8RJqDEG7B0KnRYEIQ3l00GrBgCp08FF0phhyqVg0c5IxbOmJCsZx+/fsybTn10mLZX0shFfLJDHLsBRpMh+Yz3f5IEwAO7JB0ls/bxYdw/wkeB5+NeCBqP7iID1rUHmGjSIIvMVqa3YLewfaIngFoCQKGAF7VQFFQnWCbkFsHC2EWG/WtKqAXj8klha4GhOSkKQFz4VsYJME7wVL72j8s34ilMW9vn53jr3c0Ep84HzbUQRBAA7wY9Ytch+jVrTUOfVuR2E7KaDhM4BHIWTxMedlI5W9RpMJIoZjMI2hTuF3lMYS6BhxAVxsR7ypAQbQkp+GlA1AJwTNqRp+0hgaWhkSYdAJ4lqxavJj/Vq2yFj/rFc2IlZ7nt5CYHdoJCpb3zNeb42nSsNLU2mERlt1PrGogU7wbBurTWNUWnY+Io0BE9EopCpIjBgUMkDQZDC+QSv+4pF4SSDCCtxfIGSD2FVLAClml8TC4CvHWNnLtwPFBS7QXEvOOGO3tRYvWEJH//aD2vtzy3tnjMsHebgbEHW48xXB4vdwDqehHTQy+Xfe7jJ9PVmh6z14UwVwY1W6CQ4h44eHMxl+UPdobziSx6jArlBO3UCIAA4noZnBIdhUIoUqCMo2I0yR53C+MWBSicUgKfWxNJqNU1jgoxRrEexvgBOhkZkUvK42ysHgU4crG/Lf+eRvW2jjWcALI6cPI6iEGGdbdTPWVXrE1ZxnoO3BfiatTACSoiPWAQHDaBWGBzF+W8tAoAjDCrFi10sAkUouwOUkQ9ljkKn2KmGzIQCwPmQ5x2kEmQ7MgYS8OI+5CFCHRuCQaj4HRH/Le9hrfMsf+/vuhcKH09BdPh4YJtTwzkviDQdJHAonVNadzooLAwxcKZReBxUHBgA1NFevJDtY3jKCDaElPw0YMIB4C4Qqx1u4ViMYn+SB4u1oQZDi3WRZDVb37/U9NYPiV2/Reein7ODWe57voxLsSvcmAiAxbnu4/y2LgBWrHsaGnYuVGCTFZf50FG3JYI6RnfDpFS97j77LhX8ZwvQEko+RKHddaxx4RY+0TGf+XgsJcbg7wTIeGSYCKjwM5IiFvFjbuvVJbf3VtwJuCf0ZX3J3rtN5j3wnDYInOye+6NW/Do4jBTAU5CwjTM558Kp8LDgWBSBAAEUVIR+po4DnEaZwIkGEOwaIcUG4K+kN17/h+v39+Wuhv+d+ohCUSuAXVAbV43yA8WkAuAmww2ZCw7PSRposdhgferWSBl1xLedS761r2IQLl9uMouXSs++AWmORU2T9fIGz/1iPV/yni1QH7dOeI4G0OEAd4Hi7dciGOQtZAxGQUUU0VC0KXYLqQWPCJnWetNwzcatv+zuz30xh/tCaKtbD9ZhAdru6mh0PGUAx641Jh2AbZ+IpY0YvB3TFMPCgQnjGFeosIUQMQxCSip8lhuT++hpZt958+c80N5Yf11rfeSLpk6uslG71nq61kZ1rW8WbOYQjaqbxdq1cPZaa81aY/21SP+18NXaqB91Or0trZs90bVw+FoF9TxzFcb8wpzWhu+ZQxZ8Al+FnhttiIqNGOnqycsu/GG6FAP8l/OKUYFpS30uBph0ANBHnv1EawK24akIywODxUsIxyBbFFtCQ6Fqcsk33kixbyVsPGPRnl3vPG79rfNOuGfdYUf+4seHn/STDYtOuk/OO2mjrDqsn313//zS/r2bPrJhz39/cMOu7//Vhp3r3r3hxW+v3LD9lhUbnrzp9EDnUtP/4qfnb7zp/CPuW/fJYzZ/c80JP2toie7JmLrP4x3hHQaZwZ9kGc+TAZyBmSELaiWTtaCKJYwC14NbDOevNaYUAGeELx0iWImM/8FT+HArgoRMSi75+hu65JY9qfF7BFJjjL30dNN/6dLY3r1dO3LZvr2N92yV+Q88p3M2vabNoA38hxz8EyYC7BF8Q+5UjbJt0yOvNf94m8buf0nmtovU/9OdW8/5hzu23revz/4UOeEmYV6QcZS2uQqLAkplIV9oqjWZcgC2fyqWFqsJi8zgQuAI7FmL7CEUlCBPkCccn1xy8+7Ukhu7Kt4bEAhdkzhm8OKzF/RcsFT2vtwtAwM7RPuG9tS1tO1tkhek9b7H988h5Nh9rT3PSlMkI9HWBYvsrj4ZPH+x7P/ofz3z2e4+/bmqXQkENjGbYbA66uwRx7PuUCKDngXYbrnQWnsf4005AOgrDAIyvYO82wvMFoICAjzah3dCQab4U6Yar/Pom3Z1Lr6xK0VxJTAYuFnn+I/uVuM7pYuPX9Cz+k9M9wXL5u0nVi+f383H2lXYOZfcue3sL9277eeHX7MVqWGSblwVMYQUPuCxI4WAf52QIjKOonByUKfDhmnCAQWANr1wRSxl1HYoLCYEtBSUEU5mFWQE4thFycVffVUX3/BqavENL6eOvOHlijuDc8qo4shrt8aPuHZbJ8BkxWmkcUwEB4+YCyLUR9hAlRIZ2xA2EKfrsh/r4aDh8TVq6gOuHnAAaMELV7SlPJUOtwsoYNo4GhTG1dVVqBPWmZVOyML9zy9M0qh0HvWvOxXoXHz9S6nFX37R4ciO51NFpLZ3Hpl8jtAj/vkPyt2EIcYNHOfinGh3l7MCBS54HyIwuBzvKETO3JAWhRTUHjUJAM164cq2FHIpoYoSKaRIGQWPVBKXQeBZDyGj6qVy12Zt3FpNIgsdMEcS8qRam9Tg/9oSBy8O4Vg8p4mwThucLfAiZFDGk6nFE6wVm8e7RYhsXnwAuzGNLmkVdRRRKfBhXWr+qVkAaNmOK+elX/r0fIMs7hCsOcg8MGiETJiNWJS72E6GMrZBBRd1CYEuEfAy6hOMGwjJE0FtuKRseNyCHMNpzhebzUl+MCe5gSHJ9Q1Ktm9AhnoG0s9ftzTx/LUnJLZffULiuauPTzz7eeBzxye2fe64xNbPHpsojFJTUtMAhJbtWLsgZQrfGyFb4WcVUgJMsU6eMoI8Qb4UlBGhLORJiVJ5WA8p28gL0jrkSQnKkPHieJHErm+cNS0ODn1Sjk5LADjZjs+0p3hzxhOMe2t2GcmGAlgvsAFBdpKh3GVuoU4ZdwtlbAvqw42UcRchqq6JdfKUBbwTY0cN9wkkrkzv/sZZZtfXz3I2OsmbXExbALiOHZ85NPXSVQtxX7Adyiy02AkEeQc4BXVxvBXFOR3AwocE9J2MbURQh6KMPPshxzhB3wJfrKMfeQLzoKMg89Oimtj19eUzkvX0TYhpDUA4yc7PLUrt/PzhSEjtQIFsLLTA/wXOyZjlzPZQ5njosE8oY2aP5KEAAXWCtqAOES4NxgXnLnyTGzp+1wxmvbOlULwpASjMJTu/cERq5xePgJ8QCGs74AxcyFiX5QGFQIgwmwVZS16gI+RdJmtRR5w86DusF7SzjTLU0mL9xK6bz0DWz9xxE/qhlL6pAQgn3nn1Uamd1xydevmaxcbDSxyyt3AGw1Uu7aWQuazL8AdV6Lo2J0S9oO5ko3YQHiFxc735DLPr5mUHneOd/ShmJACYt3jtvO6Y1MvXLkm8ct0xhlkqCAjhMreQ3ahLWA+oxQ4gipkPZ2vaIstVbaLrxtNN101vS+y6aVkhsMXpDjpmEgGYfttfSR2fBlLEqx3Hm1e/dIJ59csnAkvx7bEmPCMJzzMJz9rEazecYl77yimm66unEomur57mHP5WcHqpJw+qAJQaNpp/5V/+NF3EV0496DN7tP3l6m+ZAJRbwFtdPhuAGY7gbABmAzDDHpjh6Wd3wGwAZtgDMzz97A6YDcAMe2CGp5/dAVUCMN3N/w8AAP//1anZswAAAAZJREFUAwC37B/8726EIAAAAABJRU5ErkJggg=="

# Page config
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
st.set_page_config(
    page_title="QuarterCharts",
    page_icon=Image.open(BytesIO(base64.b64decode(FAVICON_B64))),
    layout="wide",
    initial_sidebar_state="auto",
)


# Cache version: only clear caches manually when needed (not on every new session)
# To force cache clear: bump this number AND uncomment the clear() line, then revert.
# _CACHE_VERSION = 91
# if st.session_state.get("_cache_v") != _CACHE_VERSION:
#     st.cache_data.clear()
#     st.session_state._cache_v = _CACHE_VERSION

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Force light mode at browser level BEFORE any content renders
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
st.markdown(
    '<meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">'
    '<meta name="google-site-verification" content="4yRIohYFN8d_gMq4yQUG3sF9n_tbeZqKEL4pp-SlK9A" />'
    '<meta name="color-scheme" content="light only">'
    '<style>:root{color-scheme:light only !important}'
    'html,body,.stApp{background:#fff!important;color:#212529!important}'
    '[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(hr){margin-top:-11px;margin-bottom:-11px}'
    '[data-testid="stSidebarUserContent"]{margin-top:-9px!important}'
    '.block-container{padding-top:68px!important}'
    '.block-container>.stVerticalBlock{row-gap:0px!important}'
    '.block-container>.stVerticalBlock>[data-testid="stElementContainer"]:has(style):not(:has(.nav-bar)){position:absolute!important;height:0!important;overflow:hidden!important}'
    '[data-testid="stHeader"]{display:none!important}'
    '[data-testid="stToolbar"]{display:none!important}'
    '[data-testid="stDecoration"]{display:none!important}'
    '[data-testid="stStatusWidget"]{display:none!important}'
    '.nav-bar{position:fixed!important;top:0!important;left:0!important;right:0!important;height:60px!important;z-index:999!important}'
    '[data-testid="stHorizontalBlock"]:has([class*="st-key-hdr_show_"]){margin-top:33px!important}'
    '[data-testid="stHorizontalBlock"]:has([class*="st-key-hdr_show_income"]){margin-top:10px!important}'
    '</style>',
    unsafe_allow_html=True,
)

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Custom CSS Ã¢ÂÂ light theme matching Quarter Charts style
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
st.markdown("""
<style>
/* ---- Variables ---- */
:root {
    --bg: #ffffff;
    --sidebar-bg: #f8f9fa;
    --header-bg: #212529;
    --accent: #2475fc;
    --text: #212529;
    --muted: #6c757d;
    --border: #dee2e6;
    --light-border: #e9ecef;
    --green: #34a853;
    --yellow: #fbbc04;
    --red: #ea4335;
}

/* ---- Global Ã¢ÂÂ force white immediately to prevent dark flash on refresh ---- */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"], .main, .block-container,
[data-testid="stMainBlockContainer"] {
    background-color: #ffffff !important;
    color: #212529 !important;
}

/* Remove Streamlit header */
[data-testid="stHeader"] {
    background-color: #ffffff !important;
    display: none !important;
}

/* Sidebar Ã¢ÂÂ move to right side */
section[data-testid="stSidebar"] {
    background-color: var(--sidebar-bg) !important;
    border-left: 1px solid var(--border);
    border-right: none;
    order: 2 !important;
    min-width: 340px !important;
    width: 340px !important;
}
/* Make collapse button always visible Ã¢ÂÂ arrow flipped to >> (close right-side sidebar) */
[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] {
    visibility: visible !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button {
    visibility: visible !important;
}
[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button [data-testid="stIconMaterial"] {
    transform: scaleX(-1) !important;
}
[data-testid="stAppViewContainer"] {
    flex-direction: row !important;
}
[data-testid="stAppViewContainer"] > div:not([data-testid="stSidebar"]) {
    order: 1 !important;
    flex: 1 1 auto !important;
}
/* Push the collapse/expand button to the right side too */
[data-testid="stSidebarCollapsedControl"] {
    left: auto !important;
    right: 0.5rem !important;
    /* Hide Streamlit's default expand control Ã¢ÂÂ we use our nav-bar button */
    opacity: 0 !important;
    pointer-events: none !important;
    position: fixed !important;
    top: -9999px !important;
}
/* When sidebar is collapsed, hide the sidebar panel */
[data-testid="stSidebar"][aria-expanded="false"] {
    min-width: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    background: transparent !important;
    border: none !important;
}
[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarContent"] {
    width: 0 !important;
    min-width: 0 !important;
    overflow: hidden !important;
}
/* Hide all sidebar content when collapsed */
[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarUserContent"] {
    display: none !important;
}

/* Ã¢ÂÂÃ¢ÂÂ CSS-driven expand-button visibility (no JS needed) Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ */
/* When sidebar is collapsed, show the nav-bar expand button via :has() */
:has([data-testid="stSidebar"][aria-expanded="false"]) .nav-expand-btn {
    display: inline-flex !important;
}
/* When sidebar is expanded, ensure the expand button hides */
:has([data-testid="stSidebar"][aria-expanded="true"]) .nav-expand-btn {
    display: none !important;
}

/* Remove default top padding, add space for fixed nav bar */
.block-container {
    padding-top: 68px !important;
    padding-bottom: 1rem !important;
}

/* ---- Nav bar (dark header) ---- */
.nav-bar {
    background: linear-gradient(135deg, #1a1f2e 0%, #0f1219 100%);
    padding: 0 36px;
    display: flex;
    align-items: center;
    gap: 0;
    flex-wrap: nowrap;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 60px;
    box-shadow: 0 1px 0 rgba(255,255,255,0.06), 0 4px 20px rgba(0,0,0,0.25);
    z-index: 999;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
/* Hide the Streamlit container that wraps the nav bar */
[data-testid="stElementContainer"]:has(.nav-bar) {
    position: absolute !important;
    height: 0 !important;
    overflow: visible !important;
    margin: 0 !important;
    padding: 0 !important;
}
.nav-expand-btn {
    display: none;
    width: 32px !important;
    height: 32px !important;
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 6px !important;
    padding: 0 !important;
    color: rgba(255,255,255,0.7) !important;
    font-size: 18px !important;
    cursor: pointer;
    transition: all 0.2s;
    line-height: 1 !important;
    align-items: center;
    justify-content: center;
    margin-left: 8px;
    flex-shrink: 0;
}
.nav-expand-btn:hover { background: rgba(255,255,255,0.2) !important; color: #fff !important; }
.nav-links {
    display: flex;
    align-items: center;
    gap: 2px;
    height: 100%;
    flex: 1;
    overflow-x: auto;
    scrollbar-width: none;
}
.nav-links::-webkit-scrollbar { display: none; }
.nav-bar a, .nav-bar .nav-link {
    color: rgba(255,255,255,0.55);
    text-decoration: none;
    font-size: 0.82rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    transition: all 0.2s ease;
    cursor: pointer;
    padding: 0 18px;
    height: 60px;
    display: flex;
    align-items: center;
    white-space: nowrap;
    border-bottom: 2px solid transparent;
    position: relative;
}
.nav-bar a:hover, .nav-bar .nav-link:hover {
    color: rgba(255,255,255,0.9);
    background: rgba(255,255,255,0.04);
}
.nav-bar a.active, .nav-bar .nav-link.active {
    color: #ffffff;
    font-weight: 600;
    border-bottom-color: #3b82f6;
}
.nav-logo {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-right: 32px;
    text-decoration: none !important;
    flex-shrink: 0;
    height: 100%;
    border-bottom: none !important;
    padding: 0 !important;
}
.nav-logo:hover { background: none !important; }
.nav-logo img { flex-shrink: 0; height: 48px; width: auto; }
.nav-logo-text {
    font-size: 0.9375rem;
    font-weight: 700;
    color: #ffffff !important;
    line-height: 1.2;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.nav-right {
    display: flex;
    align-items: center;
    gap: 4px;
    height: 100%;
    flex-shrink: 0;
    margin-left: auto;
}
.nav-right .nav-signin {
    background: #3b82f6 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    padding: 8px 20px !important;
    height: auto !important;
    border-bottom: none !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.02em !important;
    margin-left: 12px;
    transition: all 0.2s ease;
    box-shadow: 0 1px 3px rgba(59,130,246,0.3);
}
.nav-right .nav-signin:hover { background: #2563eb !important; box-shadow: 0 2px 8px rgba(59,130,246,0.4) !important; transform: translateY(-1px); }

.more-info-link {
    color: var(--accent);
    font-size: 0.8rem;
    text-decoration: none;
    cursor: pointer;
}

/* ---- Pre-style section header rows via CSS to prevent white flash on load ---- */
/* These rules ONLY apply before JS runs (no .section-row-* class yet).
   Once JS adds .section-row-expanded / .section-row-collapsed, these
   step aside and the JS-applied rules take over. */
[data-testid="stHorizontalBlock"]:has([class*="st-key-hdr_show_"]):not(.section-row-expanded):not(.section-row-collapsed) {
    background: var(--header-bg) !important;
    border-radius: 12px !important;
    border: 2px solid var(--header-bg) !important;
    padding: 0 4px !important;
    gap: 0 !important;
    align-items: center !important;
    margin-top: 33px !important;
}
[data-testid="stHorizontalBlock"]:has([class*="st-key-hdr_show_income"]):not(.section-row-expanded):not(.section-row-collapsed) {
    margin-top: 10px !important;
}
[class*="st-key-hdr_show_"] button:not(.section-header-expanded):not(.section-header-collapsed) {
    background: transparent !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 14px 20px !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    text-align: left !important;
    cursor: pointer !important;
    min-height: 3rem !important;
}
/* Pre-style PDF buttons before JS Ã¢ÂÂ only when row has no JS class yet */
[data-testid="stHorizontalBlock"]:has([class*="st-key-hdr_show_"]):not(.section-row-expanded):not(.section-row-collapsed) [class*="st-key-gen_pdf_"] button,
[data-testid="stHorizontalBlock"]:has([class*="st-key-hdr_show_"]):not(.section-row-expanded):not(.section-row-collapsed) [class*="st-key-dl_"] button {
    background: rgba(255,255,255,0.13) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.28) !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 5px 14px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    min-height: 0 !important;
    height: auto !important;
    line-height: 1.4 !important;
    white-space: nowrap !important;
}

/* ---- Section header logo (injected by JS) ---- */
.section-logo {
    height: 22px;
    width: 22px;
    object-fit: contain;
    border-radius: 4px;
    margin-right: 8px;
    vertical-align: middle;
    background: #fff;
}

/* ---- Fix popover width & position (info icon) ---- */
[data-testid="stPopoverBody"] {
    max-width: 420px !important;
    min-width: 280px !important;
}
[data-testid="stPopover"] {
    position: relative;
}
/* Style the info "i" button */
[data-testid="stPopoverButton"] {
    background: rgba(0,0,0,0.06) !important;
    border: 1px solid rgba(0,0,0,0.12) !important;
    border-radius: 50% !important;
    width: 24px !important;
    height: 24px !important;
    min-height: 24px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 0.75rem !important;
    color: #6b7280 !important;
    cursor: pointer !important;
    line-height: 1 !important;
}
[data-testid="stPopoverButton"]:hover {
    background: rgba(36,117,252,0.1) !important;
    border-color: #2475fc !important;
    color: #2475fc !important;
}

/* ---- Section header buttons Ã¢ÂÂ EXPANDED (dark, like original) ---- */
.section-header-expanded {
    background: var(--header-bg) !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    padding: 14px 20px !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    border: 2px solid var(--header-bg) !important;
    text-align: left !important;
    cursor: pointer !important;
    min-height: 3rem !important;
    margin-top: 33px !important;
}
.section-header-expanded:hover {
    background: #343a40 !important;
    border-color: #343a40 !important;
    color: #ffffff !important;
}
.section-header-expanded:focus {
    box-shadow: none !important;
    outline: none !important;
    color: #ffffff !important;
}

/* ---- Section header buttons Ã¢ÂÂ COLLAPSED (light, like original) ---- */
.section-header-collapsed {
    background: #ffffff !important;
    color: var(--text) !important;
    border-radius: 12px !important;
    padding: 14px 20px !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    border: 2px solid var(--border) !important;
    text-align: left !important;
    cursor: pointer !important;
    min-height: 3rem !important;
    margin-top: 33px !important;
}
.section-header-collapsed:hover {
    background: #f8f9fa !important;
    border-color: #ced4da !important;
    color: var(--text) !important;
}
.section-header-collapsed:focus {
    box-shadow: none !important;
    outline: none !important;
    color: var(--text) !important;
}

/* ---- Section header row: header + PDF button side by side via st.columns ---- */
/* JS adds .section-row-expanded / .section-row-collapsed to the stHorizontalBlock
   that contains the header button + PDF button columns. */
.section-row-expanded {
    background: var(--header-bg) !important;
    border-radius: 12px !important;
    border: 2px solid var(--header-bg) !important;
    padding: 0 4px !important;
    gap: 0 !important;
    align-items: center !important;
    margin-top: 33px !important;
}
        [data-testid="stHorizontalBlock"].section-row-expanded:has([class*="st-key-hdr_show_income"]),
        [data-testid="stHorizontalBlock"].section-row-collapsed:has([class*="st-key-hdr_show_income"]) {
            margin-top: 10px !important;
        }
.section-row-collapsed {
    background: #ffffff !important;
    border-radius: 12px !important;
    border: 2px solid var(--border) !important;
    padding: 0 4px !important;
    gap: 0 !important;
    align-items: center !important;
    margin-top: 33px !important;
}
/* Header button inside row should be transparent (row provides background) */
.section-row-expanded .section-header-expanded,
.section-row-collapsed .section-header-collapsed {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    margin-top: 0 !important;
}
/* PDF button dark variant (inside expanded row) */
.section-row-expanded button:not(.section-header-expanded) {
    background: rgba(255,255,255,0.13) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.28) !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 5px 14px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    min-height: 0 !important;
    height: auto !important;
    line-height: 1.4 !important;
    white-space: nowrap !important;
}
.section-row-expanded button:not(.section-header-expanded):hover {
    background: rgba(255,255,255,0.24) !important;
    border-color: rgba(255,255,255,0.45) !important;
}
/* PDF button light variant (inside collapsed row) */
.section-row-collapsed button:not(.section-header-collapsed) {
    background: rgba(0,0,0,0.05) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 5px 14px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    min-height: 0 !important;
    height: auto !important;
    line-height: 1.4 !important;
    white-space: nowrap !important;
}
.section-row-collapsed button:not(.section-header-collapsed):hover {
    background: rgba(0,0,0,0.10) !important;
    border-color: #adb5bd !important;
}
/* Remove extra padding from PDF column containers */
.section-row-expanded [data-testid="stColumn"],
.section-row-collapsed [data-testid="stColumn"] {
    padding: 0 !important;
}
.section-row-expanded [data-testid="stColumn"] [data-testid="stButton"],
.section-row-collapsed [data-testid="stColumn"] [data-testid="stButton"],
.section-row-expanded [data-testid="stColumn"] [data-testid="stDownloadButton"],
.section-row-collapsed [data-testid="stColumn"] [data-testid="stDownloadButton"] {
    margin: 0 !important;
    padding: 0 !important;
}

/* ---- Info (i) icon styling ---- */
[data-testid="stPopoverButton"] {
    background: transparent !important;
    border: 1.5px solid #adb5bd !important;
    border-radius: 50% !important;
    width: 22px !important;
    height: 22px !important;
    min-height: 22px !important;
    min-width: 22px !important;
    max-width: 22px !important;
    max-height: 22px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    opacity: 0.5;
    position: relative !important;
    margin-top: 2px !important;
    overflow: hidden !important;
}
/* Hide ALL default inner content (text "i" + chevron) */
[data-testid="stPopoverButton"] > * {
    visibility: hidden !important;
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}
/* Draw the styled "i" via ::after pseudo-element */
[data-testid="stPopoverButton"]::after {
    content: "i" !important;
    font-family: Georgia, "Times New Roman", serif !important;
    font-size: 14px !important;
    font-style: italic !important;
    font-weight: 600 !important;
    color: #6c757d !important;
    line-height: 1 !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
}
[data-testid="stPopoverButton"]:hover {
    opacity: 1 !important;
    border-color: #2475fc !important;
    background: #f0f6ff !important;
}
[data-testid="stPopoverButton"]:hover::after {
    color: #2475fc !important;
}
[data-testid="stPopoverButton"]:focus {
    box-shadow: none !important;
    outline: none !important;
}
/* Popover content panel */
[data-testid="stPopoverBody"] {
    max-width: 460px !important;
    min-width: 360px !important;
    font-size: 0.88rem !important;
    line-height: 1.6 !important;
    padding: 4px 8px !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06) !important;
}
/* Section labels inside popover */
[data-testid="stPopoverBody"] strong {
    color: #212529 !important;
}
[data-testid="stPopoverBody"] h3 {
    font-size: 1.05rem !important;
    margin: 0 0 4px 0 !important;
    padding-bottom: 8px !important;
    border-bottom: 1.5px solid #e9ecef !important;
    color: #212529 !important;
}

/* ---- Status indicator ---- */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green);
    margin-right: 6px;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
/* Hide the duplicate nav buttons row (navbar JS triggers them) */
.hidden-nav-row { display: none !important; }

/* ---- Compact chart spacing ---- */
.element-container:has(iframe) { margin-bottom: 0 !important; }

/* ---- Footer ---- */
.footer {
    background: var(--header-bg);
    color: #adb5bd;
    padding: 40px 24px;
    margin-top: 40px;
    margin-left: -1rem;
    margin-right: -1rem;
}
.footer h3 {
    color: #ffffff;
    font-size: 1rem;
    margin-bottom: 12px;
}
.footer p, .footer a {
    color: #adb5bd;
    font-size: 0.85rem;
    line-height: 1.7;
}
.footer a:hover {
    color: var(--accent);
}

/* ---- Hide Streamlit branding ---- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* ---- Expander styling ---- */
div[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 8px;
}

/* ---- Sidebar segmented buttons ---- */
section[data-testid="stSidebar"] button[kind="secondary"] {
    border: 2px solid var(--accent) !important;
    color: var(--accent) !important;
    background: #ffffff !important;
    font-weight: 500;
    padding: 0.45rem 0.2rem !important;
    min-height: 2.5rem;
    font-size: 0.9rem;
    border-radius: 0 !important;
}
section[data-testid="stSidebar"] button[kind="primary"] {
    border: 2px solid var(--accent) !important;
    background: var(--accent) !important;
    color: #fff !important;
    font-weight: 600;
    padding: 0.45rem 0.2rem !important;
    min-height: 2.5rem;
    font-size: 0.9rem;
    border-radius: 0 !important;
}

/* Connected segmented bar (applied via JS) */
.seg-connected {
    gap: 0 !important;
    border: 2px solid var(--accent) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
.seg-connected [data-testid="stColumn"] {
    padding: 0 !important;
}
.seg-connected button {
    border: none !important;
    border-radius: 0 !important;
    border-right: 1px solid rgba(36,117,252,0.3) !important;
}
.seg-connected [data-testid="stColumn"]:last-child button {
    border-right: none !important;
}

/* Custom Timeframe expander — styled dynamically via .ctf-active / .ctf-inactive classes */
section[data-testid="stSidebar"] div[data-testid="stExpander"] {
    border: 2px solid var(--accent) !important;
    border-radius: 10px !important;
    transition: opacity 0.2s, border-color 0.2s;
}
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary p {
    color: var(--accent) !important;
    font-weight: 500;
}

/* ---- Plotly - no extra background override needed with light theme ---- */
</style>
""", unsafe_allow_html=True)

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Global responsive CSS Ã¢ÂÂ all devices / all viewports
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">', unsafe_allow_html=True)
st.markdown("""
<style>
/* ====== GLOBAL RESPONSIVE ====== */

/* Ensure smooth scrolling on iOS */
html { -webkit-overflow-scrolling: touch; }

/* Fix iOS input zoom (font-size under 16px triggers zoom) */
input, select, textarea { font-size: 16px !important; }

/* Make all Plotly charts container-width responsive */
.js-plotly-plot, .plotly { width: 100% !important; }

/* Prevent horizontal overflow globally */
.main .block-container { overflow-x: hidden; }

/* Responsive images and iframes */
img, iframe, svg, canvas { max-width: 100%; height: auto; }

/* ====== TABLET (lte 1024px) ====== */
@media (max-width: 1024px) {
    /* Collapse sidebar by default on tablet */
    section[data-testid="stSidebar"] {
        min-width: 280px !important;
        width: 280px !important;
    }
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    /* Nav bar: tighter spacing */
    .nav-bar { padding: 0 20px !important; height: 52px !important; }
    .nav-bar a, .nav-bar .nav-link { font-size: 0.78rem !important; padding: 0 12px !important; height: 52px !important; }
    .nav-logo { margin-right: 20px !important; }
    .nav-logo svg { width: 28px !important; height: 28px !important; }
    .nav-logo-text { font-size: 0.9375rem !important; }
    /* Metric cards: smaller text */
    /* Footer: tighter */
    .footer {
        padding: 24px 16px !important;
    }
}

/* ====== MOBILE (lte 768px) ====== */
/* ====== MOBILE (lte 768px) ====== */
        @media (max-width: 768px) {
            /* Sidebar as overlay on mobile Ã¢ÂÂ collapsed by default */
            section[data-testid="stSidebar"] {
                position: fixed !important;
                top: 0 !important;
                right: 0 !important;
                left: auto !important;
                z-index: 999999 !important;
                height: 100vh !important;
                height: 100dvh !important;
                transition: transform 0.3s ease, visibility 0.3s ease !important;
                border-left: 1px solid var(--border) !important;
                box-shadow: -4px 0 20px rgba(0,0,0,0.15) !important;
                min-width: 85vw !important;
                width: 85vw !important;
                max-width: 340px !important;
            }
            /* Collapsed: slide off-screen to the right */
            section[data-testid="stSidebar"][aria-expanded="false"] {
                transform: translateX(100%) !important;
                visibility: hidden !important;
                box-shadow: none !important;
            }
            /* Expanded: slide in */
            section[data-testid="stSidebar"][aria-expanded="true"] {
                transform: translateX(0) !important;
                visibility: visible !important;
            }
            /* Backdrop overlay when sidebar is open on mobile */
            :has(section[data-testid="stSidebar"][aria-expanded="true"]) [data-testid="stAppViewContainer"]::before {
                content: "";
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.4);
                z-index: 999998;
                pointer-events: auto;
            }
    /* Nav bar: scrollable on mobile */
    .nav-bar { padding: 0 14px !important; height: 50px !important; }
    .block-container { padding-top: 58px !important; }
    .nav-bar a, .nav-bar .nav-link { font-size: 0.75rem !important; padding: 0 10px !important; height: 50px !important; }
    .nav-logo { margin-right: 14px !important; }
    .nav-logo svg { width: 26px !important; height: 26px !important; }
    .nav-logo-text { font-size: 0.9375rem !important; }
    .nav-right .nav-signin { padding: 6px 14px !important; font-size: 0.75rem !important; }
/* Metric cards: responsive grid */

    /* Section headers: smaller */
    .section-header-expanded,
    .section-header-collapsed,
    [class*="st-key-hdr_show_"] button {
        padding: 10px 12px !important;
        font-size: 0.95rem !important;
        min-height: 2.4rem !important;
    }
    /* Footer: single column */
    .footer {
        padding: 20px 12px !important;
        margin-left: -0.4rem !important;
        margin-right: -0.4rem !important;
    }
    /* Streamlit columns: prevent extreme squish */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    /* Popover: fit mobile screen */
    [data-testid="stPopoverBody"] {
        max-width: 90vw !important;
        min-width: 260px !important;
    }
    /* Info banner text */
    .stAlert p {
        font-size: 0.85rem !important;
    }
}

/* ====== SMALL PHONE (lte 480px) ====== */
@media (max-width: 480px) {
    .block-container {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
    }
    .nav-bar { padding: 0 10px !important; height: 46px !important; }
    .block-container { padding-top: 54px !important; }
    .nav-bar a, .nav-bar .nav-link { font-size: 0.7rem !important; padding: 0 8px !important; height: 46px !important; }
    .nav-logo { margin-right: 8px !important; }
    .nav-logo svg { width: 22px !important; height: 22px !important; }
    .nav-logo-text { display: none !important; }
    .nav-right .nav-signin { padding: 5px 12px !important; font-size: 0.7rem !important; }

    .section-header-expanded,
    .section-header-collapsed {
        padding: 8px 10px !important;
        font-size: 0.85rem !important;
    }
    /* PDF buttons in section headers */
    .section-row-expanded button:not(.section-header-expanded),
    .section-row-collapsed button:not(.section-header-collapsed) {
        font-size: 0.68rem !important;
        padding: 4px 8px !important;
    }
}

/* ====== TOUCH DEVICE IMPROVEMENTS ====== */
@media (hover: none) and (pointer: coarse) {
    /* Larger tap targets */
    .nav-bar a, .nav-bar .nav-link {
        padding: 6px 4px !important;
        min-height: 36px !important;
        display: inline-flex !important;
        align-items: center !important;
    }
    button {
        min-height: 44px;
    }
    /* Remove hover-only effects that don't work on touch */
    .section-header-expanded:hover,
    .section-header-collapsed:hover {
        background: inherit !important;
    }
}

/* ====== HIGH DPI / RETINA ====== */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
    /* Sharper borders on retina displays */
    .section-row-expanded,
    .section-row-collapsed {
        border-width: 1px !important;
    }
}

/* ====== LANDSCAPE PHONE ====== */
@media (max-height: 500px) and (orientation: landscape) {
    .nav-bar { padding: 0 16px !important; height: 44px !important; }
    .nav-bar a, .nav-bar .nav-link { height: 44px !important; }
    .block-container { padding-top: 52px !important; }
}

/* ====== PRINT ====== */
@media print {
    .nav-bar, section[data-testid="stSidebar"], .nav-expand-btn { display: none !important; }
    .block-container { padding: 0 !important; }
}

/* ====== SCROLLABLE TABLES (global) ====== */
.responsive-table-wrap {
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-bottom: 1rem;
}
.responsive-table-wrap table {
    min-width: 580px;
}
</style>
""", unsafe_allow_html=True)



# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Session state defaults
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# ---- Deferred sync: apply header-toggle flags BEFORE widgets render ----
for _sk, _ck in [("show_income", "cb_income"), ("show_cashflow", "cb_cf"),
                  ("show_balance", "cb_bs"), ("show_metrics", "cb_km")]:
    _flag = f"_sync_{_ck}"
    if _flag in st.session_state:
        st.session_state[_ck] = st.session_state[_flag]
        st.session_state[_sk] = st.session_state[_flag]
        del st.session_state[_flag]

if "ticker" not in st.session_state:
    st.session_state.ticker = "NVDA"
try:
    initialize_schema()
except Exception:
    pass  # DB may not be available in dev mode

# Restore login state from session token in URL (survives full page reloads)
restore_session()

# Handle sign-out BEFORE URL sync so the __signout__ param isn't overwritten
if st.query_params.get("page") == "__signout__":
    from auth import clear_session_state as _clear_session
    _clear_session()
    _so_ticker = st.query_params.get("ticker", "AAPL").upper().strip()
    st.session_state.page = "home"
    st.query_params.clear()
    st.query_params["page"] = "home"
    st.query_params["ticker"] = _so_ticker
    st.rerun()

# Always sync page from query params (navbar uses URL navigation)
_qp_page = st.query_params.get("page", "").lower()
_qp_ticker = st.query_params.get("ticker", "").upper().strip()
if _qp_ticker:
    st.session_state.ticker = _qp_ticker
if _qp_page in ("home", "profile", "charts", "earnings", "watchlist", "sankey", "login", "pricing", "nsfe", "privacy", "terms", "user", "dashboard"):
    st.session_state.page = _qp_page
elif "page" not in st.session_state:
    st.session_state.page = "home"
# Always keep URL in sync so browser refresh preserves the current page.
# CRITICAL: Also sync the session ID (sid) so login persists across page reloads.
_sync_page = st.session_state.page
_sync_ticker = st.session_state.ticker
_sync_sid = st.session_state.get("_server_sid", "")
_sync_params = {"page": _sync_page, "ticker": _sync_ticker}
if _sync_sid:
    _sync_params["sid"] = _sync_sid
_needs_sync = (
    st.query_params.get("page") != _sync_page
    or st.query_params.get("ticker") != _sync_ticker
    or (_sync_sid and st.query_params.get("sid") != _sync_sid)
)
if _needs_sync:
    st.query_params.update(_sync_params)
if "quarterly" not in st.session_state:
    st.session_state.quarterly = True
if "timeframe" not in st.session_state:
    st.session_state.timeframe = "2Y"
if "show_income" not in st.session_state:
    st.session_state.show_income = True
if "show_cashflow" not in st.session_state:
    st.session_state.show_cashflow = True
if "show_balance" not in st.session_state:
    st.session_state.show_balance = True
if "show_metrics" not in st.session_state:
    st.session_state.show_metrics = True
if "show_forecast" not in st.session_state:
    st.session_state.show_forecast = False
if "layout_cols" not in st.session_state:
    st.session_state.layout_cols = 2


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Helpers
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

def _trim_timeframe(df: pd.DataFrame) -> pd.DataFrame:
    """Trim DataFrame rows to match the selected timeframe."""
    tf = st.session_state.timeframe
    if df.empty or tf == "MAX":
        return df
    if tf == "CUSTOM":
        cf = st.session_state.get("custom_from")
        ct = st.session_state.get("custom_to")
        if cf and ct:
            labels = list(df.index)
            mode = st.session_state.get("custom_mode", "quarter")

            # Direct match first (quarter labels like "Q1 2024" or annual "2024")
            try:
                i_from = labels.index(cf)
                i_to = labels.index(ct)
                if i_from > i_to:
                    i_from, i_to = i_to, i_from
                return df.iloc[i_from : i_to + 1]
            except ValueError:
                pass

            # Year-based filtering: cf/ct are years like "2020", "2025"
            # but df index has quarter labels like "Q1 2024" or "FY 2024"
            if mode == "year":
                try:
                    y_from, y_to = int(cf), int(ct)
                    if y_from > y_to:
                        y_from, y_to = y_to, y_from
                    # Extract year from each label and filter
                    mask = []
                    for lbl in labels:
                        parts = str(lbl).split()
                        yr = int(parts[-1]) if parts else 0
                        mask.append(y_from <= yr <= y_to)
                    filtered = df.loc[[l for l, m in zip(labels, mask) if m]]
                    if not filtered.empty:
                        return filtered
                except (ValueError, TypeError):
                    pass

        # Legacy fallback: "custom_n" (number of periods)
        if "custom_n" in st.session_state:
            n = st.session_state.custom_n
            return df.tail(min(n, len(df)))
        return df
    n_map = {"1Y": 4, "2Y": 8, "4Y": 16}
    n = n_map.get(tf, len(df))
    if not st.session_state.quarterly:
        n = max(n // 4, 1)
    # Return all available data if we have less than requested
    return df.tail(min(n, len(df)))


def _trim_segment_timeframe(df: pd.DataFrame) -> pd.DataFrame:
    """Trim segment DataFrame to match the selected timeframe.

    Segment data may be annual (FY labels) even when quarterly mode is
    selected (FMP free tier only provides annual segments).  This function
    detects whether the data is annual or quarterly and trims accordingly.
    """
    tf = st.session_state.timeframe
    if df.empty or tf == "MAX":
        return df

    # Detect if this is annual data (FY labels) or quarterly (Q labels)
    is_annual = any(str(idx).startswith("FY") for idx in df.index)

    year_map = {"1Y": 1, "2Y": 2, "4Y": 4}
    quarter_map = {"1Y": 4, "2Y": 8, "4Y": 16}

    if is_annual:
        # Annual data: trim by number of years (match user selection exactly)
        n = year_map.get(tf, len(df))
    elif st.session_state.quarterly:
        n = quarter_map.get(tf, len(df))
    else:
        n = year_map.get(tf, len(df))

    if tf == "CUSTOM":
        cf = st.session_state.get("custom_from")
        ct = st.session_state.get("custom_to")
        if cf and ct:
            labels = list(df.index)
            mode = st.session_state.get("custom_mode", "quarter")

            # Direct label match
            try:
                i_from = labels.index(cf)
                i_to = labels.index(ct)
                if i_from > i_to:
                    i_from, i_to = i_to, i_from
                return df.iloc[i_from : i_to + 1]
            except ValueError:
                pass

            # Year-based filtering for segment data
            if mode == "year":
                try:
                    y_from, y_to = int(cf), int(ct)
                    if y_from > y_to:
                        y_from, y_to = y_to, y_from
                    mask = []
                    for lbl in labels:
                        parts = str(lbl).split()
                        yr = int(parts[-1]) if parts else 0
                        mask.append(y_from <= yr <= y_to)
                    filtered = df.loc[[l for l, m in zip(labels, mask) if m]]
                    if not filtered.empty:
                        return filtered
                except (ValueError, TypeError):
                    pass

            # Quarter labels vs FY labels mismatch: try year extraction
            try:
                cf_year = int(str(cf).split()[-1])
                ct_year = int(str(ct).split()[-1])
                if cf_year > ct_year:
                    cf_year, ct_year = ct_year, cf_year
                mask = []
                for lbl in labels:
                    parts = str(lbl).split()
                    yr = int(parts[-1]) if parts else 0
                    mask.append(cf_year <= yr <= ct_year)
                filtered = df.loc[[l for l, m in zip(labels, mask) if m]]
                if not filtered.empty:
                    return filtered
            except (ValueError, TypeError, IndexError):
                pass

        # Legacy fallback
        if "custom_n" in st.session_state:
            n = st.session_state.custom_n
            if is_annual:
                n = max(n // 4, 2)
        else:
            return df

    return df.tail(min(n, len(df)))


def _fmt(val, pct=False, dollar=False, ratio=False) -> str:
    """Quick formatting helper for metric display."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    if pct:
        return f"{val * 100:.1f}%" if abs(val) < 10 else f"{val:.1f}%"
    if dollar:
        return f"${val:,.2f}"
    if ratio:
        return f"{val:.2f}"
    return f"{val:,.2f}"


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Chart info / explanations (Ã¢ÂÂ¹Ã¯Â¸Â icon next to each chart title)
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

CHART_INFO = {
    # Ã¢ÂÂÃ¢ÂÂ Income Statement Ã¢ÂÂÃ¢ÂÂ
    "Revenue, Gross Profit, Operating and Net Income": {
        "meaning": "Revenue is total sales. Gross Profit = Revenue minus cost of goods sold. "
                   "Operating Income = Gross Profit minus operating expenses (R&D, SGA). "
                   "Net Income = the bottom line after all expenses, taxes, and interest.",
        "reading": "Look for consistent growth across all four bars. A widening gap between "
                   "Revenue and Net Income may signal rising costs. All four growing together "
                   "indicates strong, efficient scaling.",
    },
    "Revenue by Product": {
        "meaning": "Breaks down total revenue by product line or business division, "
                   "showing which segments drive the most sales.",
        "reading": "Diversified revenue across segments is healthier. A single dominant segment "
                   "means high concentration risk. Watch for new segments gaining share Ã¢ÂÂ that's "
                   "a sign of successful expansion.",
    },
    "Revenue by Geography": {
        "meaning": "Shows revenue split by geographic region (e.g. US, Europe, Asia).",
        "reading": "Geographic diversification reduces risk from any single market. Rapid growth "
                   "in new regions signals international expansion. Decline in a region may indicate "
                   "competitive pressure or macro headwinds.",
    },
    "Gross, Operating and Net Profit Margin (%)": {
        "meaning": "Margins show profitability as a percentage of revenue. Gross Margin = "
                   "(Revenue Ã¢ÂÂ COGS) / Revenue. Operating Margin includes operating costs. "
                   "Net Margin is the final profit percentage after everything.",
        "reading": "Stable or expanding margins = pricing power and operational efficiency. "
                   "Declining margins could mean rising costs, competitive pressure, or heavy "
                   "investment phases. Compare to industry peers for context.",
    },
    "Earnings Per Share (EPS)": {
        "meaning": "EPS = Net Income ÃÂ· shares outstanding. It shows how much profit is earned "
                   "per share of stock. Basic EPS uses actual shares; Diluted includes stock options.",
        "reading": "Steadily rising EPS is the single most important driver of stock price over time. "
                   "Compare Basic vs Diluted Ã¢ÂÂ a big gap means heavy stock-based compensation. "
                   "Declining EPS with growing revenue can indicate margin compression.",
    },
    "Revenue YoY Variation (%)": {
        "meaning": "Year-over-Year revenue growth rate. Shows how much revenue increased or "
                   "decreased compared to the same period one year earlier.",
        "reading": "Accelerating YoY growth = business is gaining momentum. Decelerating (but "
                   "still positive) growth is normal as companies get larger. Negative values "
                   "mean revenue is actually shrinking.",
    },
    "QoQ Revenue Variation (%)": {
        "meaning": "Quarter-over-Quarter revenue change. Compares each quarter to the previous one.",
        "reading": "QoQ can be volatile due to seasonality (e.g. Q4 holiday spending). "
                   "Look at the pattern across years, not individual quarters. Consistent negative "
                   "QoQ in non-seasonal quarters is a warning sign.",
    },
    "Operating Expenses": {
        "meaning": "R&D = Research & Development spending. SGA = Selling, General & Administrative "
                   "costs. Together they represent the main operating expenses.",
        "reading": "High R&D spending signals investment in future growth (common in tech). "
                   "Rising SGA may indicate scaling sales efforts. Ideally, operating expenses "
                   "should grow slower than revenue (operating leverage).",
    },
    "EBITDA": {
        "meaning": "Earnings Before Interest, Taxes, Depreciation & Amortization. A widely used "
                   "measure of operating cash profitability that strips out non-cash and financing items.",
        "reading": "Growing EBITDA shows the core business is generating more cash. Often used for "
                   "valuation (EV/EBITDA ratio). Comparing EBITDA to Net Income reveals the impact "
                   "of depreciation, interest, and taxes.",
    },
    "Interest and Other Income": {
        "meaning": "Non-operating income from interest earned on cash/investments and other "
                   "miscellaneous income sources outside the core business.",
        "reading": "Growing interest income often reflects a strong cash position. Large swings "
                   "may indicate one-time gains or losses. Compare to operating income to gauge "
                   "how much profit comes from non-core activities.",
    },
    "Income Tax Expense": {
        "meaning": "The total income tax paid or accrued by the company for the period.",
        "reading": "Rising tax expense usually means growing profits Ã¢ÂÂ a good sign. An unusually low "
                   "tax rate may be due to tax credits, loss carryforwards, or international structures. "
                   "Sudden jumps could indicate one-time items.",
    },
    "Income Breakdown": {
        "meaning": "A detailed decomposition of income statement line items showing how revenue "
                   "flows through to net income through various cost and expense categories.",
        "reading": "This waterfall view reveals where profit is being created and consumed. "
                   "Look for which cost buckets are growing fastest relative to revenue.",
    },
    "Per Share Metrics": {
        "meaning": "Key financial metrics divided by shares outstanding: Revenue Per Share, "
                   "Net Income Per Share, and Operating Cash Flow Per Share.",
        "reading": "These show the value each share represents. Rising per-share metrics combined "
                   "with share buybacks = double benefit for shareholders. Flat per-share metrics despite "
                   "revenue growth could mean excessive dilution.",
    },
    "Stock Based Compensation": {
        "meaning": "SBC is the cost of stock options and equity awards given to employees. "
                   "It's a non-cash expense that dilutes existing shareholders.",
        "reading": "Some SBC is normal (attracts talent), but excessive SBC eats into real returns. "
                   "Compare SBC to net income Ã¢ÂÂ if SBC is a large percentage, reported profits are "
                   "overstated relative to cash earnings.",
    },
    "Expense Ratios": {
        "meaning": "R&D, Capex, and SBC each expressed as a percentage of revenue. "
                   "Shows how much of every dollar of revenue goes to each expense category.",
        "reading": "Declining ratios = the company is getting more efficient as it scales. "
                   "Rising R&D ratio may be fine if it drives future growth. "
                   "SBC ratio above 10-15% is considered high by most investors.",
    },
    "Effective Tax Rate (%)": {
        "meaning": "The actual percentage of pre-tax income paid as taxes, calculated as "
                   "Tax Expense ÃÂ· Pre-Tax Income.",
        "reading": "Most US companies have effective rates of 15-25%. Very low rates may use "
                   "international tax structures. Rising rates compress net margins. "
                   "Volatile rates often indicate one-time items or loss carryforwards.",
    },
    "Weighted Average Shares Outstanding": {
        "meaning": "The average number of shares during the period. Basic counts actual shares; "
                   "Diluted includes potential shares from options and convertibles.",
        "reading": "Declining share count = the company is buying back stock (returns value to "
                   "shareholders). Rising share count means dilution from SBC or equity raises. "
                   "A widening gap between Basic and Diluted indicates heavy option grants.",
    },
    # Ã¢ÂÂÃ¢ÂÂ Cash Flow Statement Ã¢ÂÂÃ¢ÂÂ
    "Cash Flows": {
        "meaning": "Operating CF = cash from core business. Investing CF = cash spent on assets "
                   "(usually negative). Financing CF = cash from debt/equity (positive) or "
                   "buybacks/dividends (negative). Free CF = Operating minus CapEx.",
        "reading": "Strong operating cash flow that exceeds net income is a quality signal. "
                   "Negative investing CF is usually good (the company is investing to grow). "
                   "Free Cash Flow is what's actually available to shareholders.",
    },
    "Cash Position": {
        "meaning": "Total cash, cash equivalents, and short-term investments on the balance sheet.",
        "reading": "A growing cash pile provides flexibility for acquisitions, buybacks, or "
                   "weathering downturns. Very high cash relative to market cap may signal "
                   "undervaluation. Low cash with high debt = financial risk.",
    },
    "Capital Expenditure": {
        "meaning": "CapEx is spending on long-term assets like property, equipment, and "
                   "infrastructure. It's an investment in future capacity.",
        "reading": "Rising CapEx often precedes revenue growth (building capacity). "
                   "Compare CapEx to depreciation: CapEx > depreciation means the company is "
                   "expanding its asset base, not just maintaining it.",
    },
    # Ã¢ÂÂÃ¢ÂÂ Balance Sheet Ã¢ÂÂÃ¢ÂÂ
    "Total Assets": {
        "meaning": "Everything the company owns: cash, receivables, inventory, property, "
                   "intellectual property, goodwill, and other assets.",
        "reading": "Growing total assets generally means the company is expanding. "
                   "A shift from current to non-current assets may mean long-term investment. "
                   "Compare asset growth to revenue growth for efficiency.",
    },
    "Liabilities": {
        "meaning": "Everything the company owes: accounts payable, short-term and long-term debt, "
                   "lease obligations, and other commitments.",
        "reading": "Some leverage is healthy (amplifies returns). But liabilities growing faster "
                   "than assets = deteriorating balance sheet. Watch the current vs non-current "
                   "split Ã¢ÂÂ high current liabilities need near-term cash to service.",
    },
    "Stockholders Equity vs Total Debt": {
        "meaning": "Equity = Assets minus Liabilities (book value owned by shareholders). "
                   "Total Debt = all interest-bearing borrowings.",
        "reading": "Equity growing while debt stays flat = strengthening balance sheet. "
                   "Debt exceeding equity (D/E > 1) increases financial risk. Some mature companies "
                   "deliberately use debt for buybacks, reducing equity while boosting EPS.",
    },
    # Ã¢ÂÂÃ¢ÂÂ Key Metrics Ã¢ÂÂÃ¢ÂÂ
    "P/E Ratio": {
        "meaning": "Price-to-Earnings ratio = Stock Price ÃÂ· EPS. Shows how much investors pay "
                   "per dollar of earnings. Higher P/E = higher growth expectations.",
        "reading": "Rising P/E with stable earnings = market expects acceleration. Falling P/E "
                   "despite growing earnings = market skepticism or sector rotation. Compare to "
                   "the company's historical average and industry peers.",
    },
    "Market Capitalization": {
        "meaning": "Market Capitalization = Stock Price ÃÂ Shares Outstanding. It's the total "
                   "market value of the company.",
        "reading": "Tracks the overall size and investor sentiment about the company over time. "
                   "Rising market cap with stable P/E means earnings are growing. A surge without "
                   "earnings growth suggests multiple expansion (higher expectations).",
    },
    "Analyst Price Targets": {
        "meaning": "Consensus estimates from Wall Street analysts for future price targets "
                   "(low, median, high) and buy/hold/sell recommendations.",
        "reading": "The spread between low and high targets shows uncertainty. More 'buy' "
                   "recommendations = bullish consensus. Compare current price to the median "
                   "target to see implied upside/downside.",
    },
}


def _chart_insight(fig, ticker: str) -> str:
    """Generate a brief, dynamic insight based on the chart's actual data."""
    traces = fig.data if hasattr(fig, "data") else []
    if not traces:
        return ""

    title = getattr(fig.layout, "meta", "") or ""
    insights = []

    try:
        # Get the primary (first) trace's data
        t0 = traces[0]
        y_vals = [float(v) for v in t0.y if v is not None] if hasattr(t0, "y") and t0.y is not None else []
        x_labels = [str(v) for v in t0.x] if hasattr(t0, "x") and t0.x is not None else []

        if len(y_vals) >= 2:
            first_val, last_val = y_vals[0], y_vals[-1]
            first_label = x_labels[0] if x_labels else "start"
            last_label = x_labels[-1] if x_labels else "latest"

            # Calculate overall change
            if first_val and first_val != 0:
                pct_change = ((last_val - first_val) / abs(first_val)) * 100
                direction = "increased" if pct_change > 0 else "decreased"

                # Format the values
                def _fmt_v(v):
                    av = abs(v)
                    if av >= 1e12:
                        return f"${v/1e12:.2f}T"
                    if av >= 1e9:
                        return f"${v/1e9:.1f}B"
                    if av >= 1e6:
                        return f"${v/1e6:.0f}M"
                    if av >= 1e3:
                        return f"${v/1e3:.0f}K"
                    if av < 1 and av > 0:
                        return f"{v:.1%}"
                    return f"{v:,.0f}"

                # Check if it's a percentage metric (margins, rates)
                is_pct = any(kw in title.lower() for kw in ["margin", "%", "ratio", "rate", "variation", "yoy", "qoq"])

                if is_pct:
                    insights.append(
                        f"<b>{ticker}</b>'s {t0.name or 'metric'} went from "
                        f"{first_val:.1f}% ({first_label}) to {last_val:.1f}% ({last_label})."
                    )
                else:
                    insights.append(
                        f"<b>{ticker}</b>'s {t0.name or 'metric'} {direction} by "
                        f"{abs(pct_change):.0f}% from {_fmt_v(first_val)} ({first_label}) "
                        f"to {_fmt_v(last_val)} ({last_label})."
                    )

            # Recent trend (last 3 periods)
            if len(y_vals) >= 3:
                recent = y_vals[-3:]
                if all(recent[i] < recent[i + 1] for i in range(len(recent) - 1)):
                    insights.append("Ã°ÂÂÂ The recent trend shows consistent growth over the last 3 periods.")
                elif all(recent[i] > recent[i + 1] for i in range(len(recent) - 1)):
                    insights.append("Ã°ÂÂÂ The recent trend shows decline over the last 3 periods.")

        # Multiple traces Ã¢ÂÂ compare latest values
        if len(traces) >= 2 and len(y_vals) >= 1:
            for t in traces[1:]:
                t_y = [float(v) for v in t.y if v is not None] if hasattr(t, "y") and t.y is not None else []
                if t_y and t0.name and t.name:
                    latest_ratio = last_val / t_y[-1] if t_y[-1] and t_y[-1] != 0 else None
                    if latest_ratio and latest_ratio > 1.5:
                        insights.append(
                            f"{t0.name} is currently {latest_ratio:.1f}ÃÂ larger than {t.name}."
                        )

    except Exception:
        pass

    return " ".join(insights) if insights else f"Explore {ticker}'s data in the chart above."


def _render_chart(fig, key: str):
    """Render a chart title (with info Ã¢ÂÂ¹Ã¯Â¸Â icon) + Plotly chart below it."""
    # Extract title stored in fig.layout.meta (plain string) by charts._layout()
    chart_title = ""
    meta = getattr(fig.layout, "meta", None)
    if isinstance(meta, str) and meta:
        chart_title = meta

    _ticker = st.session_state.get("ticker", "STOCK")

    if chart_title:
        # Title row: centered title + small info icon on the right
        _tc1, _tc2 = st.columns([20, 1])
        with _tc1:
            st.markdown(
                f'<p style="text-align:center;font-weight:600;font-size:0.9rem;'
                f'margin:0 0 2px 0;color:#212529;">{chart_title}</p>',
                unsafe_allow_html=True,
            )
        with _tc2:
            info_data = CHART_INFO.get(chart_title, {})
            with st.popover("i"):
                st.markdown(f"### {chart_title}")
                # Section 1: What it means
                meaning = info_data.get("meaning", "")
                if meaning:
                    st.markdown(
                        f'<div style="margin:8px 0 12px 0;">'
                        f'<span style="color:#2475fc;font-weight:600;font-size:0.82rem;'
                        f'text-transform:uppercase;letter-spacing:0.5px;">What it means</span>'
                        f'<p style="margin:4px 0 0 0;color:#495057;font-size:0.88rem;line-height:1.55;">'
                        f'{meaning}</p></div>',
                        unsafe_allow_html=True,
                    )
                # Section 2: How to read it
                reading = info_data.get("reading", "")
                if reading:
                    st.markdown(
                        f'<div style="margin:0 0 12px 0;padding-top:8px;'
                        f'border-top:1px solid #f0f0f0;">'
                        f'<span style="color:#2475fc;font-weight:600;font-size:0.82rem;'
                        f'text-transform:uppercase;letter-spacing:0.5px;">How to read it</span>'
                        f'<p style="margin:4px 0 0 0;color:#495057;font-size:0.88rem;line-height:1.55;">'
                        f'{reading}</p></div>',
                        unsafe_allow_html=True,
                    )

    st.plotly_chart(fig, use_container_width=True, key=key, config={
        "displayModeBar": "hover",
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })


def _share_row(chart_name: str, ticker: str):
    """Render a compact share link beneath a chart (no button, avoids layout issues)."""
    # Use markdown link styled as small text Ã¢ÂÂ avoids button wrapping in narrow columns
    pass  # Share functionality removed to fix layout; can be re-added via chart toolbar


def _plotly_fig_to_mpl(pfig, figsize=(10, 5)):
    """Convert a Plotly figure to a matplotlib figure for PDF export.

    Handles grouped bar charts, stacked bar charts, and line/scatter charts.
    Uses colours from the original Plotly traces.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    import numpy as np

    traces = pfig.data if hasattr(pfig, "data") else []
    if not traces:
        return None

    # Extract title
    title = ""
    meta = getattr(pfig.layout, "meta", None)
    if isinstance(meta, str) and meta:
        title = meta
    elif hasattr(pfig.layout, "title") and hasattr(pfig.layout.title, "text"):
        title = pfig.layout.title.text or ""

    fig, ax = plt.subplots(figsize=figsize)

    bar_traces = [t for t in traces if getattr(t, "type", "bar") == "bar"]
    line_traces = [t for t in traces
                   if getattr(t, "type", "") in ("scatter", "scattergl")]

    # Detect stacked mode
    barmode = getattr(pfig.layout, "barmode", None) or "group"

    if bar_traces:
        x_labels = [str(v) for v in bar_traces[0].x]
        x_pos = np.arange(len(x_labels))

        if barmode == "stack":
            bottom = np.zeros(len(x_labels))
            for t in bar_traces:
                y_vals = np.array([float(v) if v is not None else 0 for v in t.y])
                color = getattr(t.marker, "color", None) or "#4285f4"
                if isinstance(color, (list, tuple)):
                    color = color[0] if color else "#4285f4"
                ax.bar(x_pos, y_vals, 0.7, bottom=bottom,
                       label=t.name or "", color=color, edgecolor="none")
                bottom += y_vals
        else:
            n_bars = len(bar_traces)
            width = 0.8 / max(n_bars, 1)
            for idx, t in enumerate(bar_traces):
                y_vals = [float(v) if v is not None else 0 for v in t.y]
                color = getattr(t.marker, "color", None) or "#4285f4"
                if isinstance(color, (list, tuple)):
                    color = color[0] if color else "#4285f4"
                offset = (idx - (n_bars - 1) / 2) * width
                ax.bar(x_pos + offset, y_vals, width,
                       label=t.name or "", color=color, edgecolor="none")

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)

    for t in line_traces:
        x_labels = [str(v) for v in t.x]
        y_vals = [float(v) if v is not None else 0 for v in t.y]
        color = getattr(t.marker, "color", None) or "#4285f4"
        if isinstance(color, (list, tuple)):
            color = color[0] if color else "#4285f4"
        ax.plot(range(len(y_vals)), y_vals, marker="o",
                label=t.name or "", color=color, linewidth=2)
        if not bar_traces:
            ax.set_xticks(range(len(x_labels)))
            ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)

    # Smart y-axis formatting
    def _fmt_val(v, _pos):
        if abs(v) >= 1e9:
            return f"{v / 1e9:.0f}B"
        if abs(v) >= 1e6:
            return f"{v / 1e6:.0f}M"
        if abs(v) >= 1e3:
            return f"{v / 1e3:.0f}K"
        if 0 < abs(v) < 1:
            return f"{v:.1%}"
        return f"{v:.0f}"
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_val))

    if title:
        ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    if any(getattr(t, "name", "") for t in traces):
        ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def _generate_section_pdf(figures: list, section_title: str, ticker: str) -> bytes:
    """Generate a multi-page PDF with matplotlib-rendered charts.

    Converts each Plotly figure to a matplotlib chart, then writes all
    charts into a single PDF.  No kaleido dependency required.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from io import BytesIO

    buf = BytesIO()
    added = 0

    # Fetch company logo for title page
    _logo_img = None
    try:
        import requests as _req
        from PIL import Image as _PILImage
        _logo_resp = _req.get(
            f"https://financialmodelingprep.com/image-stock/{ticker}.png",
            timeout=3,
        )
        if _logo_resp.status_code == 200 and len(_logo_resp.content) > 100:
            _logo_img = _PILImage.open(BytesIO(_logo_resp.content)).convert("RGBA")
    except Exception:
        pass

    with PdfPages(buf) as pdf:
        # Title page
        tfig = plt.figure(figsize=(11, 1))
        if _logo_img is not None:
            logo_ax = tfig.add_axes([0.28, 0.1, 0.06, 0.8])
            logo_ax.imshow(_logo_img)
            logo_ax.axis("off")
            tfig.text(0.55, 0.5, f"{ticker} \u2014 {section_title}",
                      ha="center", va="center", fontsize=20, fontweight="bold")
        else:
            tfig.text(0.5, 0.5, f"{ticker} \u2014 {section_title}",
                      ha="center", va="center", fontsize=20, fontweight="bold")
        tfig.patch.set_facecolor("white")
        pdf.savefig(tfig, bbox_inches="tight")
        plt.close(tfig)

        for pfig, _name in figures:
            traces = pfig.data if hasattr(pfig, "data") else []
            has_data = any(
                (hasattr(t, "x") and t.x is not None and len(t.x) > 0)
                or (hasattr(t, "values") and t.values is not None
                    and len(t.values) > 0)
                for t in traces
            )
            if not has_data:
                continue
            try:
                mpl_fig = _plotly_fig_to_mpl(pfig)
                if mpl_fig:
                    pdf.savefig(mpl_fig, bbox_inches="tight", dpi=150)
                    plt.close(mpl_fig)
                    added += 1
            except Exception:
                continue

    if added == 0:
        return b""
    return buf.getvalue()


def render_charts(charts: list, section: str):
    """Render a list of (figure, name) tuples in the selected column layout.

    Skips charts that have no data (empty traces) to avoid blank placeholders
    in the grid layout.  Also stores valid figures in session state for PDF export.
    """
    # Filter out empty charts (no traces or all traces have empty x)
    valid = []
    for fig, name in charts:
        traces = fig.data if hasattr(fig, "data") else []
        has_data = any(
            (hasattr(t, "x") and t.x is not None and len(t.x) > 0)
            or (hasattr(t, "values") and t.values is not None and len(t.values) > 0)
            for t in traces
        )
        if has_data:
            valid.append((fig, name))

    # Store for PDF export
    st.session_state[f"_charts_{section}"] = valid

    # Pre-generate PDF so the download button is immediately ready (single-click)
    _section_title_map = {
        "income": "Income Statement",
        "cashflow": "Cash Flow Statement",
        "balance": "Balance Sheet",
        "keymetrics": "Key Metrics",
    }
    _pdf_state_key = f"_pdf_data_{section}"
    if valid and not st.session_state.get(_pdf_state_key):
        _tk = st.session_state.get("ticker", "STOCK")
        _sec_title = _section_title_map.get(section, section.title())
        _pdf_bytes = _generate_section_pdf(valid, _sec_title, _tk)
        if _pdf_bytes:
            st.session_state[_pdf_state_key] = _pdf_bytes
            st.session_state["_need_pdf_rerun"] = True

    n_cols = st.session_state.layout_cols
    for i in range(0, len(valid), n_cols):
        cols = st.columns(n_cols)
        for j in range(n_cols):
            idx = i + j
            if idx < len(valid):
                fig, name = valid[idx]
                with cols[j]:
                    _render_chart(fig, f"{section}_{name}_{idx}")


def _section_header(title: str, emoji: str, state_key: str, cb_key: str = "",
                    charts_key: str = "") -> bool:
    """Render a clickable section header that toggles section visibility.

    Uses st.columns to place header + PDF button side by side.
    JS PASS 1 styles the parent row with matching background.
    Returns True if the section content should be displayed.
    """
    is_open = st.session_state.get(state_key, True)
    arrow = "\u25B2" if is_open else "\u25BC"
    btn_key = f"hdr_{state_key}"
    _ticker = st.session_state.get("ticker", "STOCK")

    if charts_key:
        hdr_col, pdf_col = st.columns([0.87, 0.13])
    else:
        hdr_col = st.container()
        pdf_col = None

    with hdr_col:
        if st.button(
            f"{_ticker} {title}  {arrow}",
            key=btn_key,
            use_container_width=True,
        ):
            new_val = not is_open
            st.session_state[state_key] = new_val
            if cb_key:
                st.session_state[f"_sync_{cb_key}"] = new_val
            st.rerun()

    if pdf_col is not None:
        with pdf_col:
            _pdf_state = f"_pdf_data_{charts_key}"
            if st.session_state.get(_pdf_state):
                # PDF is pre-generated Ã¢ÂÂ show single-click download button
                try:
                    st.download_button(
                        label="PDF",
                        data=st.session_state[_pdf_state],
                        file_name=f"{_ticker}_{charts_key}.pdf",
                        mime="application/pdf",
                        icon=":material/download:",
                        key=f"dl_{charts_key}",
                    )
                except TypeError:
                    st.download_button(
                        label="\u2B07 PDF",
                        data=st.session_state[_pdf_state],
                        file_name=f"{_ticker}_{charts_key}.pdf",
                        mime="application/pdf",
                        key=f"dl_{charts_key}",
                    )
            else:
                # PDF not yet generated (section not expanded yet) Ã¢ÂÂ show
                # disabled-looking placeholder that tells user to expand first
                try:
                    st.button("PDF", key=f"gen_pdf_{charts_key}",
                              icon=":material/print:", disabled=True)
                except TypeError:
                    st.button("PDF", key=f"gen_pdf_{charts_key}",
                              disabled=True)

    return is_open


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Navigation bar (dark, matching original)
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

ticker = st.session_state.ticker
current_page = st.session_state.page

# Nav bar with page switching (using <a> links for reliable navigation)
# Auth params carry login session across full page reloads caused by <a> tag navigation
_auth_params = get_auth_params()
_is_logged_in = st.session_state.get("logged_in", False)
if _is_logged_in:
    _dashboard_link = f'<a href="/?page=dashboard&ticker={ticker}{_auth_params}" target="_self" class="nav-link {"active" if current_page == "dashboard" else ""}" style="color:#3b82f6;font-weight:600;">My&nbsp;Dashboard</a>'
    _auth_link = f'{_dashboard_link}<a href="/?page=user&ticker={ticker}{_auth_params}" target="_self" class="nav-link {"active" if current_page == "user" else ""}" style="color:#3b82f6;font-weight:600;">My&nbsp;Account</a>'
else:
    _auth_link = f'<a href="/?page=login&ticker={ticker}" target="_self" class="nav-link" style="color:#3b82f6;font-weight:600;">Sign&nbsp;In</a>'
st.markdown(f'''
<style>
[data-testid="stElementContainer"]:has(.nav-bar){{position:absolute!important;height:0!important;overflow:visible!important;margin:0!important;padding:0!important}}
</style>
<div class="nav-bar">
    <a class="nav-logo" href="/?page=home&ticker={ticker}{_auth_params}" target="_self">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:48px;width:auto;" alt="QC"/>
        <span class="nav-logo-text">Quarter<br>Charts</span>
    </a>
    <div class="nav-links">
                    <a class="nav-link {'active' if current_page == 'home' else ''}" href="/?page=home&ticker={ticker}{_auth_params}" target="_self">Home</a>
        <a class="nav-link {'active' if current_page == 'charts' else ''}" href="/?page=charts&ticker={ticker}{_auth_params}" target="_self">{ticker} Charts</a>
        <a class="nav-link {'active' if current_page == 'sankey' else ''}" href="/?page=sankey&ticker={ticker}{_auth_params}" target="_self">{ticker} Sankey</a>
        <a class="nav-link {'active' if current_page == 'profile' else ''}" href="/?page=profile&ticker={ticker}{_auth_params}" target="_self">{ticker} Profile</a>
        <a class="nav-link {'active' if current_page == 'earnings' else ''}" href="/?page=earnings&ticker={ticker}{_auth_params}" target="_self">Earnings Calendar</a>
        <a class="nav-link {'active' if current_page == 'watchlist' else ''}" href="/?page=watchlist&ticker={ticker}{_auth_params}" target="_self">Watchlist</a>
    </div>
    <div class="nav-right">
        <a href="/?page=nsfe&ticker={ticker}{_auth_params}" target="_self" class="nav-link {'active' if current_page == 'nsfe' else ''}">NSFE</a>
                    <a href="/?page=pricing&ticker={ticker}{_auth_params}" target="_self" class="nav-link">Pricing</a>
                    {_auth_link}
        <button class="nav-expand-btn" id="navExpandSidebar" title="Open sidebar">&#9776;</button>
    </div>
</div>
''', unsafe_allow_html=True)

# Ã¢ÂÂÃ¢ÂÂ Sidebar expand click handler (must load with nav bar, not at page end) Ã¢ÂÂÃ¢ÂÂ
components.html("""<script>
(function() {
    var doc = window.parent.document;
    if (!doc || !doc.body) return;
    if (doc.body._osSidebarClick2) return;
    doc.body._osSidebarClick2 = true;

    function toggleSidebar(e) {
        var btn = e.target.closest('#navExpandSidebar');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();

        var sb = doc.querySelector('[data-testid="stSidebar"]');

        var eb = doc.querySelector('[data-testid="stExpandSidebarButton"]');
        if (eb) { eb.click(); return; }

        var ctrl = doc.querySelector('[data-testid="stSidebarCollapsedControl"] button');
        if (ctrl) { ctrl.click(); return; }

        if (sb) {
            var expanded = sb.getAttribute('aria-expanded');
            sb.setAttribute('aria-expanded', expanded === 'true' ? 'false' : 'true');
        }
    }

    function closeOnBackdrop(e) {
        var sb = doc.querySelector('[data-testid="stSidebar"]');
        if (!sb || sb.getAttribute('aria-expanded') !== 'true') return;
        if (!e.target.closest('[data-testid="stSidebar"]') &&
            !e.target.closest('.nav-bar') &&
            window.innerWidth <= 768) {
            var cb = sb.querySelector('[data-testid="stSidebarCollapseButton"] button');
            if (cb) { cb.click(); return; }
            sb.setAttribute('aria-expanded', 'false');
        }
    }

    doc.body.addEventListener('click', toggleSidebar);
    doc.body.addEventListener('click', closeOnBackdrop);
})();
</script>""", height=0)

# Sync parent (Streamlit Cloud wrapper) URL with the iframe URL so that
# browser refresh preserves the current page.  The Streamlit app runs inside
# a sandboxed iframe that cannot navigate its parent via target="_top", but
# same-origin history.replaceState works.
components.html("""<script>
try {
    var top = window.parent && window.parent.parent;
    if (top && top.history) {
        var s = window.parent.location.search;
        if (top.location.search !== s) {
            top.history.replaceState({}, '', '/' + s);
        }
    }
} catch(e) {}
</script>""", height=0)

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Hide Streamlit's "Running..." status widget on all pages
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
st.markdown("""<style>
    [data-testid="stStatusWidget"] { display: none !important; }
    .stSpinner { display: none !important; }
    .modebar-container { display: none !important; }
</style>""", unsafe_allow_html=True)

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Sidebar (Charts page only Ã¢ÂÂ Profile page has no sidebar)
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
with st.sidebar:
    # Styled GO button CSS
    st.markdown("""<style>
    /* Ticker search form */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
        color: #fff !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.05em !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.45rem 1.2rem !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
        background: linear-gradient(135deg, #16213e 0%, #0f3460 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25) !important;
    }
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:active {
        transform: translateY(0px) !important;
    }
    </style>""", unsafe_allow_html=True)

    # Sign In / My Account + Sign Out + My Dashboard links at the top of the sidebar
    if st.session_state.get("logged_in"):
        from auth import get_auth_params
        _auth_params = get_auth_params()
        st.markdown(f"""
    <div style="margin:-8px 0 14px 0; border-radius:10px; overflow:hidden;
                background:linear-gradient(135deg, rgba(59,130,246,0.07) 0%, rgba(99,130,246,0.04) 100%);
                border:1px solid rgba(59,130,246,0.15);">
        <a href="/?page=dashboard&ticker={ticker}{_auth_params}" target="_self"
           style="display:block; text-align:center; padding:10px 14px;
                  color:#3b82f6; font-size:0.88rem; font-weight:700; text-decoration:none;
                  letter-spacing:0.3px; transition:background 0.2s;"
           onmouseover="this.style.background='rgba(59,130,246,0.08)'"
           onmouseout="this.style.background='transparent'">
            📊 My Dashboard
        </a>
        <div style="height:1px; background:rgba(59,130,246,0.12); margin:0 12px;"></div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 14px;">
            <a href="/?page=user&ticker={ticker}{_auth_params}" target="_self"
               style="color:#64748b; font-size:0.78rem; font-weight:600; text-decoration:none;
                      transition:color 0.2s;"
               onmouseover="this.style.color='#3b82f6'" onmouseout="this.style.color='#64748b'">
                My Account
            </a>
            <a href="/?page=__signout__&ticker={ticker}{_auth_params}" target="_self"
               id="sidebar-signout-link"
               style="color:#94a3b8; font-size:0.78rem; font-weight:600; text-decoration:none;
                      transition:color 0.2s;"
               onmouseover="this.style.color='#f87171'" onmouseout="this.style.color='#94a3b8'">
                Sign Out
            </a>
        </div>
    </div>
        """, unsafe_allow_html=True)
        # Sign-out is handled early in app startup (before URL sync)
    else:
        st.markdown(f"""
    <div style="display:flex; justify-content:flex-end; margin:-8px 0 14px 0;">
        <a href="/?page=login&ticker={ticker}" target="_self"
           style="display:inline-flex; align-items:center; gap:5px; background:#3b82f6; color:#fff;
                  font-size:0.78rem; font-weight:600; padding:5px 16px; border-radius:6px;
                  text-decoration:none; white-space:nowrap; transition:background 0.2s; box-shadow:0 1px 3px rgba(59,130,246,0.25);"
           onmouseover="this.style.background='#2563eb'" onmouseout="this.style.background='#3b82f6'">
            Sign In
        </a>
    </div>
        """, unsafe_allow_html=True)

    with st.form("ticker_form", clear_on_submit=False, border=False):
        col_input, col_btn = st.columns([3, 2], vertical_alignment="bottom")
        with col_input:
            st.markdown("<style>.stTextInput label { white-space: nowrap !important; }</style>", unsafe_allow_html=True)
            new_ticker = st.text_input(
                "Type a Ticker to Explore Data:",
                value=st.session_state.ticker,
                placeholder="e.g. AAPL, MSFT, TSLA",
            ).upper().strip()
        with col_btn:
            submitted = st.form_submit_button("GO")

    if submitted and new_ticker and new_ticker != st.session_state.ticker:
        if validate_ticker(new_ticker):
            st.session_state.ticker = new_ticker
            _ticker_params = {"page": st.session_state.page, "ticker": new_ticker}
            _ticker_sid = st.session_state.get("_server_sid", "")
            if _ticker_sid:
                _ticker_params["sid"] = _ticker_sid
            st.query_params.update(_ticker_params)
            st.rerun()
        else:
            st.error(f"'{new_ticker}' not found.")

    ticker = st.session_state.ticker

    if current_page not in ("profile", "home", "earnings"):

        info = get_company_info(ticker)

        # ---- Layout selector (below ticker input) ----
        if current_page != "sankey":
            st.markdown("---")
            st.markdown("Chart Column Layout:")
            lc = st.columns(3)
            for i, (ncols, icon) in enumerate([(1, "▬"), (2, "▦"), (3, "▩")]):
                with lc[i]:
                    if st.button(
                        icon,
                        use_container_width=True,
                        type="primary" if st.session_state.layout_cols == ncols else "secondary",
                        key=f"layout_{ncols}",
                    ):
                        st.session_state.layout_cols = ncols
                        st.rerun()

        st.markdown("----")

        if current_page != "sankey":
            _is_custom_active = st.session_state.timeframe == "CUSTOM"

            # When Custom is active, dim the preset button rows
            # ---- Quarterly / Annual toggle (segmented control) ----
            # When Custom Timeframe is active, both look unselected (secondary)
            period_col = st.columns(2)
            with period_col[0]:
                if st.button(
                    "Quarterly",
                    use_container_width=True,
                    type="primary" if (st.session_state.quarterly and not _is_custom_active) else "secondary",
                ):
                    st.session_state.quarterly = True
                    if _is_custom_active:
                        st.session_state.timeframe = "1Y"
                        st.session_state.custom_panel_open = False
                    st.rerun()
            with period_col[1]:
                if st.button(
                    "Annual",
                    use_container_width=True,
                    type="primary" if (not st.session_state.quarterly and not _is_custom_active) else "secondary",
                ):
                    st.session_state.quarterly = False
                    if _is_custom_active:
                        st.session_state.timeframe = "1Y"
                        st.session_state.custom_panel_open = False
                    st.rerun()

            # ---- Timeframe buttons (segmented control) ----
            # When Custom Timeframe is active, none are highlighted
            tf_cols = st.columns(4)
            for i, tf in enumerate(["1Y", "2Y", "4Y", "MAX"]):
                with tf_cols[i]:
                    if st.button(
                        tf,
                        use_container_width=True,
                        type="primary" if (st.session_state.timeframe == tf and not _is_custom_active) else "secondary",
                        key=f"tf_{tf}",
                    ):
                        st.session_state.timeframe = tf
                        st.session_state.custom_panel_open = False
                        st.rerun()

            # JS — dim preset buttons (Quarterly/Annual + 1Y/2Y/4Y/MAX) when custom is active
            if _is_custom_active:
                components.html("""<script>
(function(){
    var apply = function(){
        var sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) return false;
        // Style only the timeframe .seg-connected wrappers (skip layout selector)
        var segs = sidebar.querySelectorAll('.seg-connected');
        var dimmed = 0;
        for (var s = 0; s < segs.length; s++){
            // Skip layout selector: its buttons contain icons (▬ ▦ ▩), not timeframe text
            var btns = segs[s].querySelectorAll('button');
            var isLayout = false;
            for (var b = 0; b < btns.length; b++){
                var t = (btns[b].innerText||'').trim();
                if (t==='\\u25AC'||t==='\\u25A6'||t==='\\u25A9'||t==='▬'||t==='▦'||t==='▩') { isLayout = true; break; }
            }
            if (isLayout) continue;
            segs[s].style.setProperty('border-color','rgba(148,163,184,0.2)','important');
            segs[s].style.setProperty('box-shadow','inset 0 0 8px rgba(99,130,246,0.12)','important');
            segs[s].style.setProperty('opacity','0.45','important');
            for (var b = 0; b < btns.length; b++){
                btns[b].style.setProperty('border-color','rgba(148,163,184,0.18)','important');
                btns[b].style.setProperty('color','rgba(148,163,184,0.7)','important');
            }
            dimmed++;
        }
        return dimmed > 0;
    };
    if (!apply()){
        var t = setInterval(function(){ if(apply()) clearInterval(t); }, 60);
        setTimeout(function(){ clearInterval(t); }, 4000);
    }
})();
</script>""", height=0, scrolling=False)
            else:
                # Restore preset buttons to normal (remove previously injected dim styles)
                # Run at multiple delays to handle Streamlit DOM patching and .seg-connected timing
                components.html("""<script>
(function(){
    var restore = function(){
        var sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) return;
        var segs = sidebar.querySelectorAll('.seg-connected');
        for (var s = 0; s < segs.length; s++){
            segs[s].style.removeProperty('border-color');
            segs[s].style.removeProperty('box-shadow');
            segs[s].style.removeProperty('opacity');
        }
        var segBtns = sidebar.querySelectorAll('.seg-connected button');
        for (var i = 0; i < segBtns.length; i++){
            segBtns[i].style.removeProperty('border-color');
            segBtns[i].style.removeProperty('color');
        }
        // Also clean any horizontal blocks with inline dim styles (before .seg-connected is added)
        var hBlocks = sidebar.querySelectorAll('[data-testid="stHorizontalBlock"]');
        for (var h = 0; h < hBlocks.length; h++){
            hBlocks[h].style.removeProperty('border-color');
            hBlocks[h].style.removeProperty('box-shadow');
            hBlocks[h].style.removeProperty('opacity');
            var btns = hBlocks[h].querySelectorAll('button');
            for (var b = 0; b < btns.length; b++){
                btns[b].style.removeProperty('border-color');
                btns[b].style.removeProperty('color');
            }
        }
    };
    // Run immediately and at multiple delays to catch all timing scenarios
    restore();
    setTimeout(restore, 100);
    setTimeout(restore, 350);
    setTimeout(restore, 850);
    setTimeout(restore, 1600);
    setTimeout(restore, 3100);
})();
</script>""", height=0, scrolling=False)

            st.markdown("---")

            # ── Custom Timeframe — By Year / By Quarter ──
            # Fetch available periods for this ticker
            _avail_q_periods = []  # quarterly labels like "Q1 2024"
            _avail_a_periods = []  # annual labels like "2024"
            try:
                _avail_q_df = get_income_statement(ticker, quarterly=True)
                if not _avail_q_df.empty:
                    _avail_q_periods = list(_avail_q_df.index)
                _avail_a_df = get_income_statement(ticker, quarterly=False)
                if not _avail_a_df.empty:
                    _avail_a_periods = list(_avail_a_df.index)
            except Exception:
                pass

            # Extract unique years from quarterly data for "By Year" mode
            _avail_years = []
            if _avail_q_periods:
                _years_set = set()
                for p in _avail_q_periods:
                    parts = p.split()
                    if len(parts) == 2:
                        _years_set.add(parts[1])
                _avail_years = sorted(_years_set)
            elif _avail_a_periods:
                _avail_years = sorted(set(str(y) for y in _avail_a_periods))

            # Session state defaults
            if "custom_mode" not in st.session_state:
                st.session_state.custom_mode = "quarter"  # "quarter" or "year"

            _is_custom = st.session_state.timeframe == "CUSTOM"

            # Auto-apply callback — also syncs quarterly flag
            def _apply_custom_range():
                st.session_state.timeframe = "CUSTOM"
                mode = st.session_state.get("custom_mode", "quarter")
                if mode == "year":
                    y_from = st.session_state.get("_cf_year_from", "")
                    y_to = st.session_state.get("_cf_year_to", "")
                    if y_from and y_to:
                        st.session_state.custom_from = y_from
                        st.session_state.custom_to = y_to
                        st.session_state.custom_mode = "year"
                        st.session_state.quarterly = False
                else:
                    qf = st.session_state.get("_cf_q_from", "")
                    qt = st.session_state.get("_cf_q_to", "")
                    if qf and qt:
                        st.session_state.custom_from = qf
                        st.session_state.custom_to = qt
                        st.session_state.custom_mode = "quarter"
                        st.session_state.quarterly = True

            # ── Custom Timeframe panel — manual toggle so clicking header activates immediately ──
            has_data = (len(_avail_years) >= 2) or (len(_avail_q_periods) >= 2)

            # Ensure open-state key exists; auto-open if already in CUSTOM mode
            if "custom_panel_open" not in st.session_state:
                st.session_state.custom_panel_open = _is_custom_active
            if _is_custom_active:
                st.session_state.custom_panel_open = True

            _panel_open = st.session_state.custom_panel_open
            _chevron = "▾" if _panel_open else "▸"

            # Header button — clicking immediately activates CUSTOM mode
            _header_label = f"{_chevron} 🎯 Custom Timeframe"
            with st.container():
                if st.button(
                    _header_label,
                    use_container_width=True,
                    key="_ctf_toggle",
                ):
                    if not _panel_open:
                        # Opening: immediately switch to CUSTOM mode
                        st.session_state.custom_panel_open = True
                        st.session_state.timeframe = "CUSTOM"
                        # Sync quarterly flag with custom mode
                        if st.session_state.custom_mode == "quarter":
                            st.session_state.quarterly = True
                        else:
                            st.session_state.quarterly = False
                        # Pre-fill range defaults if not yet set (default ~2 years)
                        if not st.session_state.get("custom_from"):
                            if st.session_state.custom_mode == "quarter" and _avail_q_periods:
                                st.session_state.custom_from = _avail_q_periods[max(0, len(_avail_q_periods) - 8)]
                                st.session_state.custom_to = _avail_q_periods[-1]
                            elif _avail_years:
                                st.session_state.custom_from = _avail_years[max(0, len(_avail_years) - 2)]
                                st.session_state.custom_to = _avail_years[-1]
                    else:
                        # Closing: collapse but keep CUSTOM active if range is set
                        st.session_state.custom_panel_open = False
                    st.rerun()

            # JS — runs after the button renders, directly styles it via parent DOM
            # Three visual states: editing (panel open), set (panel closed but custom active), inactive
            if _panel_open and _is_custom_active:
                # Editing — fully live, bright glow
                _ctf_border  = "2px solid #3b82f6"
                _ctf_color   = "#3b82f6"
                _ctf_bg      = "rgba(59,130,246,0.08)"
                _ctf_shadow  = "0 0 0 4px rgba(99,130,246,0.3)"
                _ctf_opacity = "1"
                _ctf_weight  = "700"
            elif _is_custom_active:
                # Range set, panel collapsed — visible but settled
                _ctf_border  = "2px solid rgba(59,130,246,0.5)"
                _ctf_color   = "rgba(59,130,246,0.7)"
                _ctf_bg      = "rgba(59,130,246,0.03)"
                _ctf_shadow  = "0 0 0 3px rgba(99,130,246,0.15)"
                _ctf_opacity = "0.7"
                _ctf_weight  = "600"
            else:
                # Inactive — dimmed
                _ctf_border  = "1px solid rgba(148,163,184,0.28)"
                _ctf_color   = "#94a3b8"
                _ctf_bg      = "transparent"
                _ctf_shadow  = "0 0 0 3px rgba(99,130,246,0.15)"
                _ctf_opacity = "0.5"
                _ctf_weight  = "400"
            components.html(f"""<script>
(function(){{
    var apply = function(){{
        var sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) return false;
        var btns = sidebar.querySelectorAll('div[data-testid="stButton"] > button');
        for (var i = 0; i < btns.length; i++){{
            var txt = (btns[i].innerText || btns[i].textContent || '');
            if (txt.indexOf('Custom Timeframe') !== -1){{
                var b = btns[i];
                b.style.setProperty('border',        '{_ctf_border}',   'important');
                b.style.setProperty('border-radius', '10px',            'important');
                b.style.setProperty('color',         '{_ctf_color}',    'important');
                b.style.setProperty('background',    '{_ctf_bg}',       'important');
                b.style.setProperty('box-shadow',    '{_ctf_shadow}',   'important');
                b.style.setProperty('opacity',       '{_ctf_opacity}',  'important');
                b.style.setProperty('font-weight',   '{_ctf_weight}',   'important');
                b.style.setProperty('transition',    'all 0.2s',        'important');
                return true;
            }}
        }}
        return false;
    }};
    if (!apply()){{
        var t = setInterval(function(){{ if(apply()) clearInterval(t); }}, 60);
        setTimeout(function(){{ clearInterval(t); }}, 4000);
    }}
}})();
</script>""", height=0, scrolling=False)

            # Panel body — shown when open
            if _panel_open and has_data:
                # ── Mode toggle: By Quarter / By Year ──
                _mode_cols = st.columns(2)
                with _mode_cols[0]:
                    if st.button(
                        "By Quarter",
                        use_container_width=True,
                        type="primary" if st.session_state.custom_mode == "quarter" else "secondary",
                        key="_cm_quarter",
                    ):
                        st.session_state.custom_mode = "quarter"
                        st.session_state.quarterly = True
                        st.session_state.timeframe = "CUSTOM"
                        # Reset range to quarter defaults (~2 years = 8 quarters)
                        if _avail_q_periods:
                            st.session_state.custom_from = _avail_q_periods[max(0, len(_avail_q_periods) - 8)]
                            st.session_state.custom_to = _avail_q_periods[-1]
                        st.rerun()
                with _mode_cols[1]:
                    if st.button(
                        "By Year",
                        use_container_width=True,
                        type="primary" if st.session_state.custom_mode == "year" else "secondary",
                        key="_cm_year",
                    ):
                        st.session_state.custom_mode = "year"
                        st.session_state.quarterly = False
                        st.session_state.timeframe = "CUSTOM"
                        # Reset range to year defaults (~2 years)
                        if _avail_years:
                            st.session_state.custom_from = _avail_years[max(0, len(_avail_years) - 2)]
                            st.session_state.custom_to = _avail_years[-1]
                        st.rerun()

                if st.session_state.custom_mode == "year" and len(_avail_years) >= 2:
                    _saved_yf = st.session_state.get("custom_from", _avail_years[0])
                    _saved_yt = st.session_state.get("custom_to", _avail_years[-1])
                    if " " in str(_saved_yf):
                        _saved_yf = str(_saved_yf).split()[-1]
                    if " " in str(_saved_yt):
                        _saved_yt = str(_saved_yt).split()[-1]
                    if _saved_yf not in _avail_years:
                        _saved_yf = _avail_years[0]
                    if _saved_yt not in _avail_years:
                        _saved_yt = _avail_years[-1]

                    st.markdown(
                        '<p style="color:#94a3b8;font-size:12px;margin:8px 0 4px;font-weight:600;">FROM</p>',
                        unsafe_allow_html=True,
                    )
                    st.selectbox(
                        "From Year", _avail_years,
                        index=_avail_years.index(_saved_yf),
                        key="_cf_year_from",
                        label_visibility="collapsed",
                        on_change=_apply_custom_range,
                    )
                    st.markdown(
                        '<p style="color:#94a3b8;font-size:12px;margin:6px 0 4px;font-weight:600;">TO</p>',
                        unsafe_allow_html=True,
                    )
                    st.selectbox(
                        "To Year", _avail_years,
                        index=_avail_years.index(_saved_yt),
                        key="_cf_year_to",
                        label_visibility="collapsed",
                        on_change=_apply_custom_range,
                    )

                elif st.session_state.custom_mode == "quarter" and len(_avail_q_periods) >= 2:
                    _saved_qf = st.session_state.get("custom_from", _avail_q_periods[0])
                    _saved_qt = st.session_state.get("custom_to", _avail_q_periods[-1])
                    if _saved_qf not in _avail_q_periods:
                        _saved_qf = _avail_q_periods[0]
                    if _saved_qt not in _avail_q_periods:
                        _saved_qt = _avail_q_periods[-1]

                    st.markdown(
                        '<p style="color:#94a3b8;font-size:12px;margin:8px 0 4px;font-weight:600;">FROM</p>',
                        unsafe_allow_html=True,
                    )
                    st.selectbox(
                        "From Quarter", _avail_q_periods,
                        index=_avail_q_periods.index(_saved_qf),
                        key="_cf_q_from",
                        label_visibility="collapsed",
                        on_change=_apply_custom_range,
                    )
                    st.markdown(
                        '<p style="color:#94a3b8;font-size:12px;margin:6px 0 4px;font-weight:600;">TO</p>',
                        unsafe_allow_html=True,
                    )
                    st.selectbox(
                        "To Quarter", _avail_q_periods,
                        index=_avail_q_periods.index(_saved_qt),
                        key="_cf_q_to",
                        label_visibility="collapsed",
                        on_change=_apply_custom_range,
                    )

                # Active range indicator
                if st.session_state.get("custom_from") and st.session_state.get("custom_to"):
                    st.markdown(
                        f'<p style="color:#60a5fa;font-size:12px;margin-top:8px;text-align:center;'
                        f'background:rgba(59,130,246,0.08);padding:6px 10px;border-radius:6px;">'
                        f'📊 {st.session_state["custom_from"]} → {st.session_state["custom_to"]}</p>',
                        unsafe_allow_html=True,
                    )

            elif _panel_open and not has_data:
                st.info("No data available for this ticker yet.")

            # ---- Analyst Forecast toggle ----
            st.markdown("---")
            st.session_state.show_forecast = st.toggle(
                "📊 Analyst Forecast",
                value=st.session_state.show_forecast,
            )

            # ---- Section checkboxes ----
            st.markdown("---")
            st.session_state.show_income = st.checkbox(
                "Income Statement", value=st.session_state.show_income, key="cb_income"
            )
            st.session_state.show_cashflow = st.checkbox(
                "Cash Flow Statement", value=st.session_state.show_cashflow, key="cb_cf"
            )
            st.session_state.show_balance = st.checkbox(
                "Balance Sheet", value=st.session_state.show_balance, key="cb_bs"
            )
            st.session_state.show_metrics = st.checkbox(
                "Key Metrics", value=st.session_state.show_metrics, key="cb_km"
            )

        else:
            st.markdown('<style>[data-testid="stSidebar"] [data-testid="stImage"]{display:none!important}</style>', unsafe_allow_html=True)
            # Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ Sankey Period Comparison Selector Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
            from datetime import datetime as _dt
            st.markdown('<p style="font-size:1.26rem;font-weight:600;color:#495057;margin:0 0 6px;">Compare Periods By:</p>', unsafe_allow_html=True)

            _compare_mode = st.radio(
                "Compare by",
                ["Annual", "Quarterly"],
                key="sankey_compare_mode",
                horizontal=True,
                label_visibility="collapsed",
            )

            _cur_year = _dt.now().year
            if _compare_mode == "Annual":
                _years = [str(y) for y in range(_cur_year, _cur_year - 11, -1)]
                st.session_state.sankey_period_a = st.selectbox(
                    "Period A (show in Sankey)", _years, index=0, key="sk_pa"
                )
                st.session_state.sankey_period_b = st.selectbox(
                    "Period B (compare to)", _years, index=1, key="sk_pb"
                )
                st.session_state.sankey_compare_quarterly = False
            else:
                _quarters = []
                for _y in range(_cur_year, _cur_year - 5, -1):
                    for _q in range(4, 0, -1):
                        _quarters.append(f"Q{_q} {_y}")
                st.session_state.sankey_period_a = st.selectbox(
                    "Period A (show in Sankey)", _quarters, index=0, key="sk_qa"
                )
                st.session_state.sankey_period_b = st.selectbox(
                    "Period B (compare to)", _quarters, index=4, key="sk_qb"
                )
                st.session_state.sankey_compare_quarterly = True

        # ---- Status ----
        st.markdown(
            '<span class="status-dot"></span> '
            '<span style="color:#34a853;font-size:0.85rem;">up to date</span>',
            unsafe_allow_html=True,
        )


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Page routing
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

def _render_footer():
    """Render the shared site footer on every page."""
    st.markdown(f"""
<div class="footer">
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:30px;">
        <div>
            <h3>What is QuarterCharts?</h3>
            <p>QuarterCharts is a financial visualization tool that helps investors
            track and analyse company financials through interactive charts.
            Powered by SEC EDGAR &amp; Yahoo Finance data.</p>
        </div>
        <div>
            <h3>Quick Links</h3>
            <p>
                <a href="/?page=home">Home</a><br>
                <a href="/?page=earnings">Earnings Calendar</a><br>
                <a href="/?page=watchlist">Watchlist</a><br>
                <a href="/?page=privacy">Privacy Policy</a><br>
                <a href="/?page=terms">Terms of Service</a>
            </p>
        </div>
        <div>
            <h3>Popular Companies</h3>
            <p>AAPL &middot; MSFT &middot; GOOGL &middot; AMZN &middot; NVDA &middot; TSLA &middot; META &middot; NFLX</p>
        </div>
        <div>
            <h3>Disclaimer</h3>
            <p>This app is for educational and informational purposes only.
            Data is sourced from SEC EDGAR and Yahoo Finance and may not be 100% accurate.
            Not financial advice.</p>
        </div>
    </div>
    <hr style="border-color: #495057; margin: 20px 0;">
    <p style="text-align:center; color:#6c757d;">
        &copy; {datetime.now().year} QuarterCharts &middot; Data from SEC EDGAR, FMP &amp; Yahoo Finance
    </p>
</div>
""", unsafe_allow_html=True)

if current_page == "profile":
    from profile_page import render_profile_page
    render_profile_page(ticker)
    _render_footer()
    st.stop()

if current_page == "earnings":
    # Hide sidebar on earnings page (it's a standalone page, not ticker-specific)
    from earnings_page import render_earnings_page
    render_earnings_page()
    _render_footer()
    st.stop()

if current_page == "login":
    from login_page import render_login_page
    render_login_page()
    _render_footer()
    st.stop()

if current_page == "dashboard":
    from dashboard_page import render_dashboard_page
    render_dashboard_page()
    _render_footer()
    st.stop()

if current_page == "user":
    from user_page import render_user_page
    render_user_page()
    _render_footer()
    st.stop()

if current_page == "pricing":
    from pricing_page import render_pricing_page
    render_pricing_page()
    _render_footer()
    st.stop()

if current_page == "home":
    from home_page import render_home_page
    render_home_page()
    _render_footer()
    st.stop()

if current_page == "sankey":
    from sankey_page import render_sankey_page
    render_sankey_page()
    _render_footer()
    st.stop()

if current_page == "watchlist":
    from watchlist_page import render_watchlist_page
    render_watchlist_page()
    _render_footer()
    st.stop()

if current_page == "nsfe":
    from nsfe_page import render_nsfe_page
    render_nsfe_page()
    _render_footer()
    st.stop()

if current_page == "privacy":
    from privacy_page import render_privacy_page
    render_privacy_page()
    _render_footer()
    st.stop()

if current_page == "terms":
    from terms_page import render_terms_page
    render_terms_page()
    _render_footer()
    st.stop()

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Main content area Ã¢ÂÂ fetch data & render charts (charts page only)
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

quarterly = st.session_state.quarterly

# Fetch all data in parallel (each is cached 1hr, but cold load benefits from concurrency)
from concurrent.futures import ThreadPoolExecutor as _TP
with _TP(max_workers=4) as _pool:
    _f_inc = _pool.submit(get_income_statement, ticker, quarterly)
    _f_bal = _pool.submit(get_balance_sheet, ticker, quarterly)
    _f_cf  = _pool.submit(get_cash_flow, ticker, quarterly)
    _f_fc  = _pool.submit(get_analyst_forecast, ticker)
income_df   = _f_inc.result()
balance_df  = _f_bal.result()
cashflow_df = _f_cf.result()
_forecast_future = _f_fc.result()  # used below

# Quality check: if quarterly CF data has sparse quarters (only Q1+Q4, missing Q2+Q3),
# try yfinance directly for better coverage
if quarterly and not cashflow_df.empty:
    _q_prefixes = set(lbl.split()[0] for lbl in cashflow_df.index if lbl.startswith("Q"))
    if len(_q_prefixes) < 4:  # Missing some quarterly prefixes
        try:
            import yfinance as _yf
            _stock = _yf.Ticker(ticker)
            _raw = getattr(_stock, "quarterly_cashflow", None)
            if _raw is not None and not _raw.empty:
                from data_fetcher import _build_period_df, _CF_MAP
                _yf_cf = _build_period_df(_raw, _CF_MAP, quarterly=True)
                if not _yf_cf.empty and len(_yf_cf) >= 4:
                    _yf_q_prefixes = set(lbl.split()[0] for lbl in _yf_cf.index if lbl.startswith("Q"))
                    if len(_yf_q_prefixes) >= len(_q_prefixes):
                        cashflow_df = _yf_cf
        except Exception:
            pass  # Keep existing CF data

forecast = _forecast_future  # already fetched in parallel above
# Apply timeframe trimming
income_df = _trim_timeframe(income_df)
balance_df = _trim_timeframe(balance_df)
cashflow_df = _trim_timeframe(cashflow_df)

# Compute derived data
margins_df = compute_margins(income_df)
eps_df = compute_eps(income_df, info)
# Use full data for YoY (needs history), then trim
yoy_df = _trim_timeframe(
    compute_revenue_yoy(get_income_statement(ticker, quarterly=quarterly))
)
shares = info.get("shares_outstanding")
per_share_df = compute_per_share(income_df, cashflow_df, shares)
qoq_df = _trim_timeframe(
    compute_qoq_revenue(get_income_statement(ticker, quarterly=quarterly))
)
expense_ratios_df = compute_expense_ratios(income_df, cashflow_df)
ebitda_df = compute_ebitda(income_df, cashflow_df)
tax_rate_df = compute_effective_tax_rate(income_df)

# Try quarterchart.com source for Expense Ratios / Per Share / EBITDA (more reliable data)
try:
    _qc_expense = _trim_timeframe(_opensankey_get_segments(ticker, 14, quarterly=quarterly))
    if not _qc_expense.empty and len(_qc_expense) >= 2:
        # Rename to match chart expectations
        _rename = {}
        for c in _qc_expense.columns:
            cl = c.lower()
            if "r&d" in cl or "research" in cl or "developement" in cl:
                _rename[c] = "R&D to Revenue"
            elif "capex" in cl:
                _rename[c] = "Capex to Revenue"
            elif "stock" in cl or "sbc" in cl:
                _rename[c] = "SBC to Revenue"
        if _rename:
            expense_ratios_df = _qc_expense.rename(columns=_rename)
except Exception:
    pass

try:
    _qc_pershare = _trim_timeframe(_opensankey_get_segments(ticker, 13, quarterly=quarterly))
    if not _qc_pershare.empty and len(_qc_pershare) >= 2:
        _rename = {}
        for c in _qc_pershare.columns:
            cl = c.lower()
            if "revenue" in cl:
                _rename[c] = "Revenue Per Share"
            elif "net income" in cl:
                _rename[c] = "Net Income Per Share"
            elif "operating" in cl or "cash flow" in cl:
                _rename[c] = "Operating Cash Flow Per Share"
        if _rename:
            per_share_df = _qc_pershare.rename(columns=_rename)
except Exception:
    pass

try:
    _qc_ebitda = _trim_timeframe(_opensankey_get_segments(ticker, 5, quarterly=quarterly))
    if not _qc_ebitda.empty and len(_qc_ebitda) >= 2:
        ebitda_df = _qc_ebitda
except Exception:
    pass

income_breakdown_df = pd.DataFrame()
try:
    _qc_incbreak = _trim_timeframe(_opensankey_get_segments(ticker, 12, quarterly=quarterly))
    if not _qc_incbreak.empty and len(_qc_incbreak) >= 2:
        income_breakdown_df = _qc_incbreak
except Exception:
    pass
# Revenue segmentation (product & geography)
product_seg_df = _trim_segment_timeframe(get_revenue_by_product(ticker, quarterly=quarterly))
geo_seg_df = _trim_segment_timeframe(get_revenue_by_geography(ticker, quarterly=quarterly))

# If no data at all
if income_df.empty and balance_df.empty and cashflow_df.empty:
    st.error(
        f"Could not load financial data for **{ticker}**. "
        "This might be due to network issues or the ticker not having "
        "financial statements available on Yahoo Finance."
    )
    _render_footer()
    st.stop()


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Analyst Forecast Section (only if toggle is on)
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

if st.session_state.show_forecast and forecast:
    # Analyst Forecast has no collapse Ã¢ÂÂ always show if toggled on
    _section_header("Analyst Forecast", "Ã°ÂÂÂ", "show_forecast", "")

    if st.session_state.show_forecast:
        fc_cols = st.columns(4)
        with fc_cols[0]:
            st.metric("Mean Target", f"${forecast.get('target_mean', 0):.2f}")
        with fc_cols[1]:
            st.metric("High Target", f"${forecast.get('target_high', 0):.2f}")
        with fc_cols[2]:
            st.metric("Low Target", f"${forecast.get('target_low', 0):.2f}")
        with fc_cols[3]:
            upside = forecast.get("upside_pct", 0)
            st.metric(
                "Upside",
                f"{upside:+.1f}%",
                delta=f"{upside:+.1f}%",
                delta_color="normal" if upside > 0 else "inverse",
            )

        rec = forecast.get("recommendation", "")
        n_analysts = forecast.get("num_analysts", "N/A")
        st.caption(f"Recommendation: **{rec.upper() if rec else 'N/A'}** · Analysts: **{n_analysts}**")

        _render_chart(create_analyst_forecast_chart(forecast), "analyst_chart")


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Income Statement Section Ã¢ÂÂ header ALWAYS visible
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

_section_header("Income Statement", "Ã°ÂÂÂ", "show_income", "cb_income", charts_key="income")

if st.session_state.show_income:
    income_charts = [
        (create_income_chart(income_df), "revenue_income"),
    ]
    # Revenue segmentation charts (FMP key required)
    if not product_seg_df.empty:
        income_charts.append((create_revenue_by_product_chart(product_seg_df), "rev_product"))
    if not geo_seg_df.empty:
        income_charts.append((create_revenue_by_geography_chart(geo_seg_df), "rev_geo"))
    if not margins_df.empty:
        income_charts.append((create_margins_chart(margins_df), "margins"))
    if not eps_df.empty:
        income_charts.append((create_eps_chart(eps_df), "eps"))
    if not yoy_df.empty:
        income_charts.append((create_revenue_yoy_chart(yoy_df), "yoy"))
    if not qoq_df.empty:
        income_charts.append((create_qoq_revenue_chart(qoq_df), "qoq"))

    income_charts.append((create_opex_chart(income_df), "opex"))
    if not ebitda_df.empty:
        income_charts.append((create_ebitda_chart(ebitda_df), "ebitda"))
    income_charts.append((create_tax_chart(income_df), "tax"))
    # Build a richer SBC df: if expense_ratios has SBC-to-Revenue, back out dollar SBC
    _sbc_df = cashflow_df
    if (not expense_ratios_df.empty and "SBC to Revenue" in expense_ratios_df.columns
            and not income_df.empty and "Revenue" in income_df.columns):
        _common = expense_ratios_df.index.intersection(income_df.index)
        if len(_common) >= 2:
            _sbc_vals = (expense_ratios_df.loc[_common, "SBC to Revenue"]
                         * income_df.loc[_common, "Revenue"])
            _sbc_df = pd.DataFrame({"Stock Based Compensation": _sbc_vals}, index=_common)
    income_charts.append((create_sbc_chart(_sbc_df), "sbc"))

    if not expense_ratios_df.empty:
        income_charts.append((create_expense_ratios_chart(expense_ratios_df), "expense_ratios"))
    if not tax_rate_df.empty:
        income_charts.append((create_effective_tax_rate_chart(tax_rate_df), "eff_tax_rate"))

    income_charts.append((create_shares_chart(income_df), "shares"))

    if not income_breakdown_df.empty:
        income_charts.append((create_income_breakdown_chart(income_breakdown_df), "income_breakdown"))

    if not per_share_df.empty:
        income_charts.append((create_per_share_chart(per_share_df), "per_share"))

    render_charts(income_charts, "income")


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Cash Flow Section Ã¢ÂÂ header ALWAYS visible
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

_section_header("Cash Flow Statement", "Ã°ÂÂÂ°", "show_cashflow", "cb_cf", charts_key="cashflow")

if st.session_state.show_cashflow:
    render_charts([
        (create_cash_flow_chart(cashflow_df), "cash_flows"),
        (create_cash_position_chart(balance_df), "cash_pos"),
        (create_capex_chart(cashflow_df), "capex"),
    ], "cashflow")


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Balance Sheet Section Ã¢ÂÂ header ALWAYS visible
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

_section_header("Balance Sheet", "Ã°ÂÂÂ¦", "show_balance", "cb_bs", charts_key="balance")

if st.session_state.show_balance:
    render_charts([
        (create_assets_chart(balance_df), "assets"),
        (create_liabilities_chart(balance_df), "liabilities"),
        (create_equity_debt_chart(balance_df), "equity_debt"),
    ], "balance")


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Key Metrics Section Ã¢ÂÂ header ALWAYS visible
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

_section_header("Key Metrics", "Ã°ÂÂÂ", "show_metrics", "cb_km", charts_key="keymetrics")

if st.session_state.show_metrics:
    km_charts = []

    # P/E Ratio over time
    if not eps_df.empty and "EPS" in eps_df.columns and info.get("current_price"):
        pe_df = pd.DataFrame(index=eps_df.index)
        price = info["current_price"]
        pe_df["P/E Ratio"] = (price / eps_df["EPS"].replace(0, np.nan)).round(2)
        pe_df = pe_df.dropna()
        if not pe_df.empty:
            km_charts.append((create_pe_chart(pe_df), "pe_ratio"))

    # Metric cards
    m1 = st.columns(4)
    with m1[0]:
        st.metric("Gross Margin", _fmt(info.get("gross_margins"), pct=True))
    with m1[1]:
        st.metric("Operating Margin", _fmt(info.get("operating_margins"), pct=True))
    with m1[2]:
        st.metric("ROE", _fmt(info.get("return_on_equity"), pct=True))
    with m1[3]:
        st.metric("ROA", _fmt(info.get("return_on_assets"), pct=True))

    m2 = st.columns(4)
    with m2[0]:
        st.metric("Debt/Equity", _fmt(info.get("debt_to_equity"), ratio=True))
    with m2[1]:
        st.metric("Current Ratio", _fmt(info.get("current_ratio"), ratio=True))
    with m2[2]:
        st.metric("Quick Ratio", _fmt(info.get("quick_ratio"), ratio=True))
    with m2[3]:
        st.metric("Revenue Growth", _fmt(info.get("revenue_growth"), pct=True))

    if km_charts:
        render_charts(km_charts, "keymetrics")




# Footer
# ───────────────────────────────────────────────────────────────────────────

_render_footer()



# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# JavaScript: Style section header buttons + connected segmented controls
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

components.html("""
<script>
(function initQuarterCharts() {
    // Access the parent document (Streamlit main frame)
    var doc = window.parent.document;

    function applyStyles() {
        var main = doc.querySelector('.stMainBlockContainer') || doc.querySelector('[data-testid="stAppViewContainer"]');
        if (!main) return;

        // ---- PASS 0: Clean stale section-row-* classes from ALL blocks ----
        // Streamlit recycles DOM elements across reruns, so a block that was
        // a header row in a previous render may now hold chart content.
        var staleRows = main.querySelectorAll('.section-row-expanded, .section-row-collapsed');
        for (var sr = 0; sr < staleRows.length; sr++) {
            staleRows[sr].classList.remove('section-row-expanded', 'section-row-collapsed');
        }
        var staleBtns = main.querySelectorAll('.section-header-expanded, .section-header-collapsed');
        for (var sb = 0; sb < staleBtns.length; sb++) {
            staleBtns[sb].classList.remove('section-header-expanded', 'section-header-collapsed');
        }

        // ---- PASS 1: Style section header buttons ----
        var sectionNames = ['Income Statement', 'Cash Flow', 'Balance Sheet',
                            'Key Metrics', 'Analyst Forecast'];
        var allBtns = main.querySelectorAll('button');
        for (var i = 0; i < allBtns.length; i++) {
            var text = allBtns[i].textContent || '';
            var isSection = false;
            for (var s = 0; s < sectionNames.length; s++) {
                if (text.indexOf(sectionNames[s]) !== -1) { isSection = true; break; }
            }
            if (!isSection) continue;
            allBtns[i].classList.add(
                (text.indexOf(String.fromCharCode(0x25B2)) !== -1)
                    ? 'section-header-expanded' : 'section-header-collapsed'
            );

            // Inject company logo into section header button
            if (!allBtns[i].querySelector('.section-logo')) {
                var words = text.trim().split(/\s+/);
                var ticker = words[0];
                if (ticker && ticker.length <= 6) {
                    var img = document.createElement('img');
                    img.src = 'https://financialmodelingprep.com/image-stock/' + ticker + '.png';
                    img.className = 'section-logo';
                    img.onerror = function() { this.style.display = 'none'; };
                    var span = allBtns[i].querySelector('p') || allBtns[i];
                    span.insertBefore(img, span.firstChild);
                }
            }

            // Style the parent stHorizontalBlock row (contains header + PDF columns)
            var row = allBtns[i].closest('[data-testid="stHorizontalBlock"]');
            if (row) {
                row.classList.add(
                    (text.indexOf(String.fromCharCode(0x25B2)) !== -1)
                        ? 'section-row-expanded' : 'section-row-collapsed'
                );
            }
        }

        // ---- Sidebar segmented controls ----
        var sidebar = doc.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            var hBlocks = sidebar.querySelectorAll('[data-testid="stHorizontalBlock"]');
            for (var h = 0; h < hBlocks.length; h++) {
                var cols = hBlocks[h].querySelectorAll('[data-testid="stColumn"]');
                if (cols.length < 2) continue;
                var allBtns = true;
                for (var c = 0; c < cols.length; c++) {
                    if (!cols[c].querySelector('button')) { allBtns = false; break; }
                }
                if (allBtns) {
                    hBlocks[h].classList.add('seg-connected');
                }
            }
        }
    }

    // Apply immediately and after delays for Streamlit lazy rendering
    setTimeout(applyStyles, 300);
    setTimeout(applyStyles, 800);
    setTimeout(applyStyles, 1500);
    setTimeout(applyStyles, 3000);

    // Fix popover width via JS (emotion CSS overrides regular CSS)
    function fixPopoverWidth() {{
        var popovers = doc.querySelectorAll('[data-testid="stPopoverBody"]');
        for (var i = 0; i < popovers.length; i++) {{
            var el = popovers[i];
            el.style.setProperty('max-width', '420px', 'important');
            el.style.setProperty('min-width', '300px', 'important');
            el.style.setProperty('width', 'auto', 'important');
        }}
    }}

    setTimeout(fixPopoverWidth, 500);
    setTimeout(fixPopoverWidth, 1500);


    // Re-apply on DOM mutations (Streamlit re-renders)
    var observer = new MutationObserver(function() {
        setTimeout(applyStyles, 100);
        setTimeout(fixPopoverWidth, 50);
    });
    observer.observe(doc.body, { childList: true, subtree: true });

    // Sidebar click handler is in a separate early-loading components.html
    // near the nav bar (not here) so it loads before the page finishes.

    // Fix popover width - Streamlit emotion CSS overrides regular CSS
    (function() {
        var popoverObserver = new MutationObserver(function(mutations) {
            var popovers = document.querySelectorAll('[data-testid="stPopoverBody"]');
            popovers.forEach(function(el) {
                if (!el._popoverFixed) {
                    el.style.setProperty('max-width', '420px', 'important');
                    el.style.setProperty('min-width', '280px', 'important');
                    el._popoverFixed = true;
                }
            });
        });
        popoverObserver.observe(document.body, { childList: true, subtree: true });
    })();

})();
</script>
""", height=0)

# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Auto-rerun once after PDFs are pre-generated so download buttons appear
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
if st.session_state.pop("_need_pdf_rerun", False):
    st.rerun()
