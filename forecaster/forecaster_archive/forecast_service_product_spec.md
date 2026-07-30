# Forecast Service Product Spec (v1)

## Product summary
A simple forecasting service for small businesses that helps users predict what is likely to happen next based on their own data. The experience is anonymous-first, explainable, and privacy-safe.

## Problem
Small business owners often need help with decisions such as:
- how much inventory to buy
- how much seed or material to order
- how many trips or deliveries to expect
- how many temporary workers to plan for

Many of them do not have a data science background and need a tool that is simple and easy to trust.

## Core product promise
Users can upload their own data, receive a forecast, and get a simple recommendation without creating an account.

## Target users
- sole proprietors
- small retail shops
- landscapers
- delivery or service businesses
- other small businesses with simple recurring demand patterns

## Core principles
- anonymous first
- intuitive and explainable
- no storage of user data by default
- no code execution from uploaded files
- clear plain-language guidance

## Initial user flow
1. User opens the service.
2. User uploads a CSV or Excel file.
3. The app validates the file.
4. The system analyzes the data and generates a forecast.
5. The app shows:
   - the forecast for the next period
   - a plain-language explanation
   - a recommended action when enough context exists
6. The user can download or copy the result.
7. If the user wants to save results later, optional account creation can be offered.

## First-version features
### Input
- upload CSV or Excel
- simple drag-and-drop upload
- required columns validation
- file size limit

### Forecasting
- basic trend-based forecasting
- seasonal pattern detection when enough data exists
- simple forecast for next period or next few periods

### Output
- plain-language summary
- confidence or reliability note
- recommended action such as reorder, hire, or plan more trips

### Privacy and safety
- no forced login
- temporary session-based processing
- no raw data stored by default
- uploaded files deleted after processing
- isolated processing environment

## Example outputs
- “Demand is likely to rise next month. You may want to order about 15% more stock.”
- “Your workload is expected to increase over the next two weeks. Consider scheduling extra support.”

## Success criteria
- users can upload data and get a forecast in under 2 minutes
- users understand the result without technical help
- users trust the guidance enough to act on it
- the system protects privacy and avoids data leakage

## Non-goals for v1
- complex custom models
- user-defined code or formulas
- deep integrations with many business systems
- long-term data history or advanced analytics

## Recommended next step
Build a simple MVP around a single anonymous workflow:
- upload file
- validate file
- generate forecast
- show plain-language explanation and recommendation
