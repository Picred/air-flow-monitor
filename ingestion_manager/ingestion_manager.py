import asyncio
import json
import sys
import time
from utils.retrieve_data import (
    get_states_by_country,
    get_cities_by_state_country,
    make_request,
    get_data,
    check_api_key
)
from utils.setup import logger, config, LOGSTASH_HOSTNAME, LOGSTASH_PORT
from utils.logstash_handler import LogstashHandler
from utils.train_data import CSVHandler


async def retrieve_and_send_data(logstash_handler: LogstashHandler, csv_handler: CSVHandler):
    """
    Retrieves and sends air quality data to Logstash.

    Args:
        logstash_handler (LogstashHandler): The handler for sending data to Logstash.
    """
    logger.info("Starting data ingestion process...")
    logger.info("This is not a demo. Real data will be retrieved. It may take a while. 🕒")
    logger.info("Selected country: %s", config['COUNTRY_NAME'])
    logger.info("Retrieving data of major cities...")

    states = get_states_by_country(config['COUNTRY_NAME'])
    states_list = [elem['state'] for elem in states]

    time.sleep(1)

    for state in states_list:
        state = state.replace(" ", "+")
        logger.info("State retrieved: %s", state)
        cities = get_cities_by_state_country(state, config['COUNTRY_NAME'])

        if not cities:
            continue

        cities_list = [elem['city'] for elem in cities if 'city' in elem]
        if not cities_list:
            logger.warning("No cities found for this state. Maybe too many requests.\
                            Waiting 10 sec. [CTRL+C to stop]")
            time.sleep(10)
            continue

        logger.info("Retrieved cities %s", cities_list)
        time.sleep(10)

        city = cities_list[0].replace(" ", "+")
        logger.info("City selected: %s", city)
        url = f"http://api.airvisual.com/v2/city?city={city}&state={state}&country=\
            {config['COUNTRY_NAME']}&key={config['API_KEY']}"
        response = make_request(url)

        if csv_handler:
            csv_handler.write_to_csv(response)
        else:
            logstash_handler.send_to_logstash(response)

        time.sleep(10)


def get_demo_data() -> dict:
    """
    Retrieves all demo data from a given json file.
    """
    with open(file='demo_data.json', mode='r', encoding='utf-8') as f:
        return json.load(f)


async def demo(logstash_handler: LogstashHandler):
    """
    Demo function to test the data ingestion process.

    Args:
        logstash_handler (LogstashHandler): The handler for sending data to Logstash.
    """
    demo_data = get_demo_data()
    for element in demo_data:
        logstash_handler.send_to_logstash(element.get("data"))


async def main():
    """
    The main asynchronous function for executing the script.
    """
    csv_handler = CSVHandler("/ingestion_manager/data/historical_data.csv")

    logstash_handler = LogstashHandler(LOGSTASH_HOSTNAME, LOGSTASH_PORT)
    # logstash_handler.test_logstash() # Comment to get data for training

    data_action = config['DATA_ACTION']
    if data_action == "DEMO":
        await demo(logstash_handler)
    elif data_action == "NODEMO":
        # await retrieve_and_send_data(logstash_handler=logstash_handler, csv_handler=None) # Comment to get data for training
        await retrieve_and_send_data(logstash_handler=None, csv_handler=csv_handler) # Uncomment to train data
    else:
        logstash_handler.send_to_logstash(get_data())


if __name__ == '__main__':
    if not check_api_key():
        logger.error("API_KEY environment variable not set!!")
        sys.exit(1)
    logger.info("API_KEY is set 👌")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program exited")
