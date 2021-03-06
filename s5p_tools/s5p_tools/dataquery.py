"""
Set of tools to query Copernicus database.
"""

from os import listdir, rename, makedirs
from os.path import exists
import concurrent.futures

from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt, InvalidChecksumError, SentinelAPIError
from ..pretty_print import printBold, printCyan, printRed


def query_copernicus_hub(aoi=None, username='s5pguest', password='s5pguest', hub='https://s5phub.copernicus.eu/dhus', **kwargs):
    """
    Query Copernicus Open access Hub.

    :param aoi: (str) Geojson Area of interest url
    :param username: (str) Username to use for API connection
    :param password: (str) Password to use for API connection
    :param hub: (str) Url of hub to query
    :param kwargs: (dict) extra keywords for the api.query function (see https://sentinelsat.readthedocs.io/en/stable/cli.html#sentinelsat)
    :return: (SentinelAPI, dict) API object and results of query
    """

    # connect to the API
    api = SentinelAPI(username, password, hub)

    # query database
    if aoi is None:
        products = api.query(**kwargs)
    else:
        # convert .geojson file
        footprint = geojson_to_wkt(read_geojson(aoi))
        products = api.query(footprint, **kwargs)

    # display results
    printBold('Number of products found: {number_product}\nTotal products size: {size} MB\n'.format(
        number_product=len(products),
        size=sum([float(products[uuid]['size'][:-3]) for uuid in products.keys()])))

    return api, products


def get_filenames_request(products, download_directory='L2_data'):
    """
    Get local files url corresponding to a Copernicus request (must be already downloaded)

    :param products: (dict) Copernicus Hub query
    :param download_directory: (str) Url of folder for downloaded products
    :return: (list) List of strings with local urls for each product in the request
    """

    # list of id's per requested products
    ids_request = list(products.keys())

    # list of downloaded filenames urls
    filenames = [f"{download_directory}/{products[file_id]['title']}.nc" for file_id in ids_request]

    return filenames


def request_copernicus_hub(aoi=None, login='s5pguest', password='s5pguest', hub='https://s5phub.copernicus.eu/dhus',
                           download_directory='L2_data', checksum=True, fix_extension=True, **kwargs):
    """
    Query Copernicus Open access Hub and download automatically files that are not already downloaded.

    :param aoi: (str) Geojson Area of interest url
    :param username: (str) Username to use for API connection
    :param password: (str) Password to use for API connection
    :param hub: (str) Url of hub to query
    :param download_directory: (str) Url of folder for downloaded products
    :param checksum: (bool) Verify product integrity after download
    :param fix_extension: (bool) Fix extension from .zip to .nc (see https://github.com/sentinelsat/sentinelsat/issues/270)
    :param kwargs: (dict) extra keywords for the api.query function (see https://sentinelsat.readthedocs.io/en/stable/cli.html#sentinelsat)
    :return: (SentinelAPI, dict) API object and results of query
    """

    api, products = query_copernicus_hub(aoi, login, password, hub, **kwargs)
    ids_request = list(products.keys())
    makedirs(download_directory, exist_ok=True)

    for file_id in ids_request:

        if not exists(f"{download_directory}/{products[file_id]['title']}.nc"):

            # file not already downloaded
            print(f"File {file_id} not found. Downloading into {download_directory}")
            try:
                api.get_product_odata(file_id)
            except SentinelAPIError:
                printRed(f"Error: File {file_id} not found in Hub. Skipping")
            else:
                while True:
                    try:
                        api.download(file_id, directory_path=download_directory, checksum=checksum)
                    except InvalidChecksumError:
                        printRed("Invalid Checksum Error. Trying again...")
                        continue
                    else:
                        # fix .zip extention
                        if fix_extension:
                            rename(f"{download_directory}/{products[file_id]['title']}.zip",
                                   f"{download_directory}/{products[file_id]['title']}.nc")
                        break

        else:
            print(f"File {file_id} already exists")

    return api, products
