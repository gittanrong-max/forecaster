# Anonymous-First Forecast Service Plan

## Product goal
Build a forecasting service for small businesses where users can upload their own data, receive a forecast, and get simple next-step guidance without being forced to create an account.

## Core product principles
- Treat every user as anonymous by default.
- Do not require login for basic use.
- Do not store user data unless the user explicitly opts in.
- Make forecasts intuitive, explainable, and easy to understand.
- Support many business types with a general forecasting experience.

## Anonymous-first experience
- Users can start immediately without signing up.
- The service should work with a temporary session.
- The system should not assume identity or persistence unless needed.
- If the user wants to save results, revisit past forecasts, or receive alerts, offer optional account creation later.

## Privacy and safety rules
- Treat uploaded files as untrusted input.
- Never execute user-provided code.
- Never allow arbitrary scripts, macros, or formulas.
- Accept only a narrow set of safe input formats, such as CSV or Excel.
- Validate file structure strictly before processing.
- Process each job in isolation.
- Delete uploaded data and temporary files after the forecast is generated unless the user opts in to saving it.

## Security architecture
### 1. Frontend
- Users upload a file or enter data.
- The app sends the request to the backend.
- The app displays only the forecast and a plain-language explanation.

### 2. Backend
- Accept uploads through a secure API.
- Validate file type, size, and schema.
- Convert the data into a safe internal format.
- Send the parsed data to an isolated forecasting worker.
- Remove temporary files after processing.

### 3. Forecasting worker
- Runs in an isolated container or sandbox.
- Has no access to other users’ data.
- Can only read the current job’s input.
- Cannot access secrets or the main database.

### 4. Data storage
- Store only the minimum necessary metadata, such as:
  - job ID
  - timestamp
  - forecast result
  - optional user session ID
- Avoid storing raw uploaded files by default.
- If storage is necessary, encrypt it and delete it automatically after a short retention period.

## Access control
- Since most users are anonymous, the system should use temporary session-based access.
- Each forecasting job should be associated with a temporary session token.
- The token should allow access only to that one job.
- No user should be able to access another user’s results.
- If an account is later introduced, switch to per-user access control.

## Anti-abuse protections
- Limit file size.
- Limit the number of uploads per session.
- Reject unexpected formats and malformed files.
- Log suspicious behavior without exposing sensitive data.
- Rate-limit requests to reduce abuse.

## Product experience
### Forecasting behavior
- The service should predict what is likely to happen next.
- It should explain the result in simple language.
- If enough information is available, it should suggest a next action, such as:
  - reorder inventory
  - increase staffing
  - plan extra trips
  - buy more supplies

### Explainability
- Show simple reasons such as:
  - recent trend
  - seasonality
  - recent changes in demand
- Avoid technical jargon.
- Use plain-language summaries like:
  - “Demand is rising, so you may need more stock next month.”

## MVP recommendation
For the first version, focus on:
- anonymous upload
- CSV or Excel input
- strict validation
- isolated processing
- simple forecast output
- plain-language recommendations
- no persistent storage by default

## Future optional features
- Optional account creation for saving forecasts
- Email or notification reminders
- Saved templates by business type
- History of past forecasts
- Team sharing for business users

## Bottom line
The safest way to keep the product flexible is to support many business types through a narrow, controlled input format and a temporary, isolated processing model. That allows the service to stay simple for users while protecting privacy and reducing security risk.
