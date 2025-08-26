# DataMetronome Podium API - Postman Collection Setup

This directory contains a complete Postman collection and environment for testing the DataMetronome Podium API.

## Files

- **`DataMetronome_Podium_API.postman_collection.json`** - Complete API collection with all endpoints
- **`DataMetronome_Podium_Environment.postman_environment.json`** - Environment variables for local development
- **`POSTMAN_SETUP.md`** - This setup guide

## Quick Start

### 1. Import the Collection

1. Open Postman
2. Click **Import** button
3. Drag and drop `DataMetronome_Podium_API.postman_collection.json` or click **Upload Files** to select it
4. The collection will appear in your Postman workspace

### 2. Import the Environment

1. In Postman, click **Import** again
2. Drag and drop `DataMetronome_Podium_Environment.postman_environment.json`
3. The environment will be available in your environments dropdown

### 3. Select the Environment

1. In the top-right corner of Postman, select **"DataMetronome Podium - Local Development"** from the environments dropdown
2. This will activate all the environment variables

## Environment Variables

The environment includes the following key variables:

### Core Configuration
- **`base_url`** - API base URL (default: `http://localhost:8000`)
- **`api_version`** - API version (default: `v1`)

### Authentication
- **`access_token`** - JWT token for authenticated requests (auto-populated after login)
- **`test_username`** - Default test username (default: `admin`)
- **`test_password`** - Default test password (default: `admin`)
- **`test_email`** - Default test email (default: `admin@datametronome.dev`)

### Test Data IDs
- **`stave_id`** - ID of a data source for testing
- **`clef_id`** - ID of a rule set for testing
- **`user_id`** - ID of a user for testing
- **`check_run_id`** - ID of a check run for testing

### Test Data Values
- **`test_stave_name`** - Sample stave name for creation
- **`test_clef_name`** - Sample clef name for creation
- **`test_check_parameters`** - Sample check parameters
- **`test_check_metadata`** - Sample check metadata

## API Endpoints Overview

### 1. Root & Health
- **GET /** - API information and version
- **GET /health** - Health check

### 2. Authentication
- **POST /api/v1/auth/login** - User login
- **POST /api/v1/auth/register** - User registration
- **GET /api/v1/auth/me** - Get current user info

### 3. Data Sources (Staves)
- **GET /api/v1/staves/** - List all staves
- **GET /api/v1/staves/{id}** - Get stave by ID
- **POST /api/v1/staves/** - Create new stave
- **PUT /api/v1/staves/{id}** - Update stave
- **DELETE /api/v1/staves/{id}** - Delete stave

### 4. Rule Sets (Clefs)
- **GET /api/v1/clefs/** - List all clefs
- **GET /api/v1/clefs/{id}** - Get clef by ID
- **POST /api/v1/clefs/** - Create new clef
- **PUT /api/v1/clefs/{id}** - Update clef
- **DELETE /api/v1/clefs/{id}** - Delete clef

### 5. Data Quality Checks
- **POST /api/v1/checks/{clef_id}/run** - Execute a check
- **GET /api/v1/checks/history** - Get check history

### 6. Metrics & Dashboard
- **GET /api/v1/metrics/dashboard** - Get dashboard metrics
- **GET /api/v1/metrics/health** - Metrics service health

### 7. Reporting
- **GET /api/v1/reports/health** - System health report
- **GET /api/v1/reports/summary** - Summary report
- **GET /api/v1/reports/checks** - Checks report
- **GET /api/v1/reports/anomalies** - Anomalies report

## Testing Workflow

### Step 1: Authentication
1. Start with the **"User Login"** request
2. Use the default credentials: `admin` / `admin`
3. Copy the `access_token` from the response
4. Set the `access_token` environment variable with this value

### Step 2: Create Test Data
1. **Create New Stave** - Create a data source
2. Copy the returned `stave_id` to the environment variable
3. **Create New Clef** - Create a rule set (use the `stave_id` from step 2)
4. Copy the returned `clef_id` to the environment variable

### Step 3: Test Operations
1. **Get All Staves** - Verify the stave was created
2. **Get All Clefs** - Verify the clef was created
3. **Run Check** - Execute a data quality check
4. **Get Check History** - View check results

### Step 4: Reporting & Metrics
1. **Get Dashboard Metrics** - View overall system status
2. **Get System Health Report** - Generate health report
3. **Get Summary Report** - View aggregated metrics

## Prerequisites

Before using this collection, ensure:

1. **DataMetronome Podium API is running** on `http://localhost:8000`
2. **Database is initialized** and accessible
3. **Environment variables are set** (see `env.example` in the project root)

## Running the API Locally

```bash
# Navigate to the podium directory
cd datametronome/podium

# Install dependencies
pip install -r requirements.txt

# Set environment variables (copy from env.example)
cp ../env.example .env
# Edit .env with your configuration

# Run the API
python -m datametronome_podium.main
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure the API is running on the correct port
   - Check if the port is available and not blocked by firewall

2. **Authentication Errors**
   - Verify the `access_token` is set correctly
   - Check if the token has expired (default: 30 minutes)
   - Ensure the user exists in the database

3. **404 Not Found**
   - Verify the API endpoints match the collection
   - Check if the API version is correct (`v1`)
   - Ensure the base URL is correct

4. **500 Internal Server Error**
   - Check the API logs for detailed error messages
   - Verify database connectivity
   - Check environment variable configuration

### Debug Mode

Enable debug mode by setting:
```bash
export DATAMETRONOME_DEBUG=true
```

This will provide more detailed logging and error information.

## Collection Features

### Pre-request Scripts
- Automatically sets `Accept: application/json` header for all requests

### Test Scripts
- Validates response status codes (200 or 201)
- Ensures JSON content type
- Checks response time (< 5 seconds)

### Variables
- Dynamic URL construction using environment variables
- Reusable test data across requests
- Easy switching between environments

## Contributing

When adding new endpoints to the API:

1. Update the collection with new requests
2. Add relevant environment variables
3. Update this documentation
4. Test the new endpoints thoroughly

## Support

For issues with the API:
- Check the API logs
- Review the `TESTING_GUIDE.md` in the project root
- Consult the `README.md` in the podium directory

For issues with the Postman collection:
- Verify the collection version matches your API version
- Check environment variable values
- Ensure all required headers are set
