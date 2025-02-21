# Loyverse Scraper

Automated scraper for Loyverse data that runs both locally and in GitHub Actions.

## Setup

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd loyverse-scraper
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

4. Edit `.env` with your credentials and configuration.

### GitHub Actions Setup

1. Go to your repository's Settings > Secrets and Variables > Actions
2. Add the following secrets:
   - `LOYVERSE_ACCOUNTS`: JSON string containing account information
   - `TWOCAPTCHA_API_KEY`: Your 2captcha API key
   - `EMAIL_USERNAME`: Email sender username
   - `EMAIL_PASSWORD`: Email sender password
   - `EMAIL_RECIPIENTS`: Comma-separated list of email recipients

## Usage

### Local Run

```bash
python -m src.scraper
```

### GitHub Actions

The scraper will run automatically at 8:00 AM Malaysia time daily. You can also trigger it manually from the Actions tab in GitHub.

## Configuration

### Account Configuration Format

```json
[
  {
    "email": "example@email.com",
    "password": "example_password",
    "invalid_outlets": ["outlet1", "outlet2"]
  }
]
```

## Development

- The code is structured to be modular and maintainable
- Core functionality is separated into utilities
- Configuration is handled via environment variables
- Error handling and logging are implemented throughout

## Notes

- The script uses headless Chrome in GitHub Actions
- Captcha solving is handled via 2captcha
- Excel reports are generated with conditional formatting
- Reports are sent via email after successful execution

## Troubleshooting

### Common Issues

1. Captcha Issues:
   - Check 2captcha API key
   - Ensure sufficient balance in 2captcha account

2. Login Problems:
   - Verify account credentials
   - Check for any account lockouts

3. Excel Generation Issues:
   - Ensure write permissions in output directory
   - Check for file locks

### GitHub Actions Issues

1. Workflow Failures:
   - Check secrets are properly configured
   - Verify environment variables
   - Review workflow logs for detailed error messages