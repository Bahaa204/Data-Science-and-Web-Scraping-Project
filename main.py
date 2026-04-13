import streaming_services_scrapper
import steam_scrapper
import data_cleaning
import data_analysis
import Machine_Learning
import EDA
import NLP_Processing


def main() -> None:
    print("Running Streaming Services Scraper: ")
    streaming_services_scrapper.main()

    print("Running Steam Scraper: ")
    steam_scrapper.main()

    print("Running Data Cleaning: ")
    data_cleaning.main()

    print("Running Data Analysis: ")
    data_analysis.main()

    print("Training some Models: ")
    Machine_Learning.main()

    print("Running EDA analysis: ")
    EDA.main()

    print("Running NLP Processing: ")
    NLP_Processing.main()

    print("Finished")


if __name__ == "__main__":
    main()
