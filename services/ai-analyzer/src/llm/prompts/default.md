# Default Trading Analysis Prompt

Analyze the following trading report and provide structured analysis with these sections:

## Summary
Executive summary (150-250 words) of key findings and recommendations.

## Market Analysis
Market observations, trends, and economic factors mentioned in the report.

## Trading Operations
If you identified specific trading operations (BUY/SELL/HOLD signals), provide as JSON array with objects containing:
action, symbol, entry_price, target_price, stop_loss, timeframe, confidence_score.
Only include if you found actual trading signals. If no operations found, omit this section.

## Risk Assessment
Risk factors, market risks, and mitigation strategies.

## Additional Insights
Any other relevant observations or notable patterns.

REPORT CONTENT:
{content}

Return ONLY the analysis with markdown sections, no preamble or extra formatting.
