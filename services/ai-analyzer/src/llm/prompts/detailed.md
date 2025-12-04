# Detailed Trading Analysis Prompt

Provide a comprehensive analysis of the following trading report with detailed sections:

## Summary
Detailed executive summary (300-400 words) of key findings, trends, and strategic recommendations.

## Market Analysis
Deep dive into market observations, technical levels, macro-economic factors, and sentiment analysis.

## Trading Operations
If you identified specific trading operations, provide as detailed JSON array with:
- action (BUY/SELL/HOLD/LONG/SHORT/CALL/PUT/SPREAD)
- symbol (ticker)
- entry_price, target_price, stop_loss
- quantity (if mentioned)
- timeframe (intraday/swing/long-term)
- confidence_score (0.0-1.0)
- reasoning (brief explanation)
Only include if you found actual trading signals. If no operations found, omit this section.

## Technical Analysis
Chart patterns, support/resistance levels, moving averages, indicators if mentioned.

## Fundamental Analysis
Company metrics, earnings, news impact, sector trends if relevant.

## Risk Assessment
Detailed risk factors, market risks, position sizing considerations, mitigation strategies.

## Additional Insights
Sector rotation opportunities, correlations, macro events, notable patterns.

REPORT CONTENT:
{content}

Return ONLY the analysis with detailed markdown sections, no preamble.
