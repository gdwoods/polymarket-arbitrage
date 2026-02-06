"""
Streamlit monitoring dashboard for Polymarket arbitrage.
"""

import asyncio
from datetime import date
import sys
from pathlib import Path

# Allow running as script: streamlit run polymarket_app/dashboard.py
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from polymarket_app.config import MIN_PROFIT_THRESHOLD
from polymarket_app.data import GammaClient, ClobClient
from polymarket_app.arbitrage import detect_single_condition_arbitrage


def run_async(coro):
    """Run async code in Streamlit."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def main() -> None:
    st.set_page_config(
        page_title="Polymarket Arbitrage",
        page_icon="📊",
        layout="wide",
    )
    st.title("Polymarket Arbitrage Monitor")
    st.caption(
        "Based on 'Unravelling the Probabilistic Forest' (arXiv:2508.03474) | "
        "Single-condition arbitrage: YES + NO ≠ $1"
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        limit = st.slider("Markets to scan", 5, 50, 15)
        min_profit = st.slider("Min profit %", 0.1, 20.0, 3.0) / 100
        with st.expander("Resolution date filter", expanded=False):
            use_date_filter = st.checkbox("Filter by resolution date", value=False)
            end_date_min = end_date_max = None
            if use_date_filter:
                d_min = st.date_input("From", value=date.today())
                d_max = st.date_input("To", value=date(2027, 12, 31))
                end_date_min = d_min.isoformat()
                end_date_max = d_max.isoformat() + "T23:59:59Z"
        price_source = st.radio(
            "Price source",
            ["CLOB price API", "Order book", "Gamma"],
            index=0,
            help="CLOB price: /price endpoint (often works for more markets). Order book: best bid/ask. Gamma: normalized, usually sum=1.",
        )

    if st.button("Run Scan", type="primary"):
        with st.spinner("Fetching markets and order books..."):
            gamma = GammaClient()
            clob = ClobClient()

            async def fetch_ob(tid):
                try:
                    return await clob.get_order_book(tid)
                except Exception:
                    return None

            async def scan():
                markets = await gamma.fetch_active_markets(
                    limit=limit,
                    end_date_min=end_date_min,
                    end_date_max=end_date_max,
                )
                binary = [
                    m
                    for m in markets
                    if len(m.clob_token_ids) >= 2
                    and m.clob_token_ids[0]
                    and m.clob_token_ids[1]
                ]
                sem = asyncio.Semaphore(10)
                async def bf(tid):
                    async with sem:
                        return await fetch_ob(tid)
                for m in binary:
                    obs = await asyncio.gather(
                        bf(m.clob_token_ids[0]),
                        bf(m.clob_token_ids[1]),
                    )
                    m.order_book_yes, m.order_book_no = obs[0], obs[1]
                opps = []
                opps_any = []
                sum_prices_list = []
                use_ob = price_source == "Order book"
                use_clob_price = price_source == "CLOB price API"
                for m in binary:
                    clob_prices = None
                    if use_clob_price:
                        clob_prices = await clob.get_clob_prices(
                            m.clob_token_ids[0],
                            m.clob_token_ids[1],
                            m.outcomes,
                        )
                        if clob_prices:
                            sum_prices_list.append(clob_prices["buy"].sum_prices)
                            sum_prices_list.append(clob_prices["sell"].sum_prices)
                    elif use_ob:
                        ob_prices = m.get_order_book_prices()
                        if ob_prices:
                            sum_prices_list.extend([ob_prices["buy"].sum_prices, ob_prices["sell"].sum_prices])
                        else:
                            gp = m.get_prices()
                            if gp:
                                sum_prices_list.append(gp.sum_prices)
                    else:
                        gp = m.get_prices()
                        if gp:
                            sum_prices_list.append(gp.sum_prices)
                    opps.extend(detect_single_condition_arbitrage(m, min_profit=min_profit, use_order_book=use_ob, clob_prices=clob_prices))
                    opps_any.extend(detect_single_condition_arbitrage(m, min_profit=0.0, use_order_book=use_ob, clob_prices=clob_prices))
                return opps, opps_any, len(binary), sum_prices_list

            opps, opps_any, n_markets, sum_prices_list = run_async(scan())

        st.success(f"Scanned {n_markets} markets. Found {len(opps)} opportunities.")
        if opps:
            import pandas as pd
            def _market_url(o) -> str:
                base = "https://polymarket.com/event/"
                es, ms = getattr(o, "event_slug", "") or "", o.slug or ""
                if es:
                    return f"{base}{es}/{ms}" if ms and ms != es else f"{base}{es}"
                return f"{base}{ms}" if ms else "https://polymarket.com"

            def _res_date(o) -> str:
                ed = getattr(o, "end_date", "") or ""
                if not ed:
                    return "—"
                try:
                    return ed[:10] if len(ed) >= 10 else ed
                except Exception:
                    return "—"

            df = pd.DataFrame(
                [
                    {
                        "Question": o.question[:60] + "..." if len(o.question) > 60 else o.question,
                        "Direction": o.direction,
                        "Resolution": _res_date(o),
                        "YES": f"{o.price_yes:.3f}",
                        "NO": f"{o.price_no:.3f}",
                        "Sum": f"{o.sum_prices:.3f}",
                        "Profit %": f"{o.profit_margin*100:.2f}%",
                        "Max USD": f"${o.max_extractable_usd():.2f}" if o.max_extractable_usd() else "—",
                        "Link": _market_url(o),
                    }
                    for o in opps[:50]
                ]
            )
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Link": st.column_config.LinkColumn("Trade", display_text="Open on Polymarket"),
                },
                hide_index=True,
            )
        else:
            st.info("No arbitrage above threshold. Markets may be efficiently priced.")
            if opps_any:
                st.warning(f"Found {len(opps_any)} opportunities at 0% threshold (below your {min_profit*100:.2f}% minimum):")
                import pandas as pd
                def _url(o):
                    es, ms = getattr(o, "event_slug", "") or "", o.slug or ""
                    if es:
                        return f"https://polymarket.com/event/{es}/{ms}" if ms and ms != es else f"https://polymarket.com/event/{es}"
                    return f"https://polymarket.com/event/{ms}" if ms else ""
                df_any = pd.DataFrame([
                    {
                        "Question": o.question[:50] + "..." if len(o.question) > 53 else o.question,
                        "Dir": o.direction,
                        "YES": f"{o.price_yes:.3f}", "NO": f"{o.price_no:.3f}",
                        "Sum": f"{o.sum_prices:.3f}", "Profit%": f"{o.profit_margin*100:.2f}%",
                        "Link": _url(o),
                    }
                    for o in opps_any[:15]
                ])
                st.dataframe(df_any, use_container_width=True, hide_index=True, column_config={"Link": st.column_config.LinkColumn("Trade", display_text="Open")})
            if sum_prices_list:
                import pandas as pd
                df_diag = pd.Series(sum_prices_list)
                with st.expander("📊 Price diagnostics"):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Min sum (YES+NO)", f"{float(df_diag.min()):.4f}")
                    with col_b:
                        st.metric("Max sum (YES+NO)", f"{float(df_diag.max()):.4f}")
                    with col_c:
                        near_buy = sum(1 for s in sum_prices_list if s < 0.99)
                        near_sell = sum(1 for s in sum_prices_list if s > 1.01)
                        st.metric("Near arb (<0.99 or >1.01)", f"{near_buy} buy / {near_sell} sell")
                    st.caption("If all sums are ≈1.00, markets are efficiently priced. Try lowering min profit or uncheck order book to use Gamma prices.")

    st.divider()
    st.markdown("""
    ### Architecture
    - **Data**: Gamma API (markets) + CLOB REST (order books)
    - **Detection**: Order book best bid/ask (YES + NO ≠ $1)
    - **Next**: Bregman projection, Frank-Wolfe, multi-condition dependencies
    """)


if __name__ == "__main__":
    main()
