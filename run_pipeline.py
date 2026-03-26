

from src.extract.emdat_extract import downlod_emdat
from src.extract.gdacs_extract import get_gdcs
from src.extract.worldbank_extract import worldbank_indicators


def execute_pipeline():

    print("Starting the pipeline")

    # download EM-DAT
    downlod_emdat()

    # download World bank data with indicators
    worldbank_indicators()

    # GDACS alerts
    get_gdcs()


# default function
if __name__ == "__main__":
    execute_pipeline()