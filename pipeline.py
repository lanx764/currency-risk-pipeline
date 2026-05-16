import requests
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    pass


class ExtractionError(Exception):
    pass


class TransformationError(Exception):
    pass


class PipelineConfig:
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        self.base_currency = os.getenv("BASE_CURRENCY")
        self.risk_threshold = float(os.getenv("RISK_THRESHOLD"))
        self.output_path = os.getenv("OUTPUT_PATH")


def validate_env(required_variables):
    missing = []
    for var in required_variables:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")
    return True


class CurrencyExtractor:
    def __init__(self, config):
        self.config = config

    def fetch_rates(self):
        try:
            response = requests.get(f"https://v6.exchangerate-api.com/v6/{self.config.api_key}/latest/{self.config.base_currency}")
            if response.status_code != 200:
                raise ExtractionError(f"Extraction failed: {response.status_code}")
        except requests.exceptions.ConnectionError:
            raise ExtractionError("Extraction failed due to connection error")
        else:
            data = response.json()
            return data


class RiskTransformer:
    def __init__(self, config):
        self.config = config

    def transform(self, data):
        transformed_data = []
        data = data["conversion_rates"]
        for key, value in data.items():
            if value is None or not isinstance(value, (int, float)):
                print(f"{key} was skipped because of missing or non-numeric value")
                continue
            my_dict = {"currency": key, "rate": value, "risk_flag": abs(value - 1.0) > self.config.risk_threshold}
            transformed_data.append(my_dict)
        df = pd.DataFrame(transformed_data)
        if df.empty:
            raise TransformationError("Transformation failed: DataFrame is empty")
        return df


def save_report(df, output_path):
    directory = os.path.dirname(output_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    df.to_csv(output_path, index=False)
    print(f"Report saved to {output_path}")


def main():
    try:
        validate_env(["API_KEY", "BASE_CURRENCY", "RISK_THRESHOLD", "OUTPUT_PATH"])
        config = PipelineConfig()
    except ConfigError as e:
        print(e)
        return None

    try:
        extractor = CurrencyExtractor(config)
        data = extractor.fetch_rates()
    except ExtractionError as e:
        print(e)
        return None

    try:
        transformer = RiskTransformer(config)
        df = transformer.transform(data)
    except TransformationError as e:
        print(e)
        return None
    else:
        print(df)
        save_report(df, config.output_path)
        flagged = df[df["risk_flag"]]
        print(f"{len(flagged)} currencies were flagged as high risk")


if __name__ == "__main__":
    main()