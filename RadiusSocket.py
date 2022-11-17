import binascii, socket, struct, os, time, traceback, uuid
from datetime import datetime
from collections import defaultdict
import pandas as pd
import multiprocessing as mp
import logging
from azure.cosmos import CosmosClient
from azure.cosmos.partition_key import PartitionKey

from DictionariesRadius import attributes

packet_max = 4096
RadiusServer = "0.0.0.0"
RaidusPort = 1887
RadiusBind = (RadiusServer, RaidusPort)
path = r'/app/Files'

cosmos_url = r'https://aprodcazamasivosdb.documents.azure.com:443'
cosmos_key = 'DTr22ugifqv3WwEwPOBG9W1lmABZ58AXwEvPuEC0s99kcYZvupQY899mA9rFIpi8XOJ9CEa4fMAZVfmAQNJUJA=='
database_name = 'CAZAMASIVOSDB'
container_name = 'EVENTOS'


translate_rules = {
    'string': lambda x: str(x.decode()),
    'integer': lambda x: int(binascii.hexlify(x), 16),
    'octeto': lambda x: oct(translate_rules.get('integer')(x)),
    'ip': lambda x: socket.inet_ntoa(x),
    'date': lambda x: datetime.fromtimestamp(translate_rules.get('integer')(x)).strftime('%Y-%m-%d %H:%M:%S'),
    'ipv6prefix': lambda x: binascii.hexlify(x),
}

translate = defaultdict(lambda x: x, **translate_rules)

mandatory_fields = [
    'id',
    'User-Name', 
    'NAS-IP-Address',
    'NAS-Port',
    'Framed-IP-Address',
    'Framed-IP-Netmask',
    'Vendor-Specific',
    'NAS-Identifier',
    'Acct-Status-Type',
    'Acct-Input-Octets',
    'Acct-Output-Octets',
    'Acct-Session-Time',
    'Acct-Input-Packets',
    'Acct-Output-Packets',
    'Acct-Terminate-Cause',
    'Event-Timestamp',
    'NAS-Port-Type',
    'NAS-Port-Id'
]


def socket_connect():
    status = False
    radiusServerSocket = None
    while not status:
        try:
            radiusServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
            radiusServerSocket.bind(RadiusBind)
            status = True
            logging.info("conecto a server")
            print("Conecto")
        except OSError:
            print("Error de conexion")
            logging.Error("no hay conexion")
            time.sleep(3)
    return radiusServerSocket


def download_data():
    status = True
    close_connection = True
    while status:
        if close_connection:
            radiusServerSocket = socket_connect()
            close_connection = False
        file_name = datetime.now().strftime("%Y%m%d%H%M%S%f")
        try:
            data = radiusServerSocket.recv(packet_max)
            with open(os.path.join(path, f'{file_name}.txt'), "wb") as file:
                file.write(data)
                logging.info(file+"log cantidades y horas ")
        except:
            radiusServerSocket.close()
            close_connection = True


def upload_data():
    status = True
    while status:
        files = os.listdir(path)
        result_list = []
        base_df = pd.DataFrame(columns = mandatory_fields)
        for file in files:
            data = None
            full_path_file = os.path.join(path, file)

            if(os.path.exists(full_path_file)):
                try:
                    with open(full_path_file, 'rb') as data:
                        data = bytearray(data.read())
                        logging.info("data",data)
                    code, id, length, authenticator = struct.unpack('!BBH16s', data[:20])
                    pos, attrs = 0, {}
                    data_2 = data[20:length]
                    logging.info("variable data2",data_2)
                    while pos < len(data_2):
                        code, length = struct.unpack('BB', data_2[pos:pos + 2])
                        attrs[attributes.get(code).get('field')] = str(translate.get(attributes.get(code).get('type'))(data_2[pos + 2:pos + length]))
                        pos += length
                    result_list.append({ mandatory_field: attrs[mandatory_field]  for mandatory_field in mandatory_fields if (mandatory_field in attrs.keys())})
                    result_df = pd.DataFrame(result_list)
                    result_df.insert(loc=0, column='id', value=str(uuid.uuid4()))
                    logging.info(result_df+"result_df")
                    base_df = base_df.merge(result_df, how = 'outer')[mandatory_fields]
                     logging.info(base_df,"basedf")
                    if (len(data) > 1):
                        os.remove(full_path_file)
                        logging.warning("se elimino data")
                except Exception as e:
                    print(e)
                    print(traceback.format_exc())
                    continue
        try:
            if len(base_df) > 0: 
                database = get_cosmos_database()
                create_container(database)
                container = database.get_container_client(container_name)
                base_df = base_df.astype(str)
                [container.upsert_item(body_dict) for body_dict in base_df.to_dict(orient="records")]
                logging.warning("base_df nuevamente",base_df)
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            continue


def clean_base():
    while True:
        database = get_cosmos_database()
        database.delete_container(container_name)
        logging.warning("se elimino contenedor")
        create_container(database)
        time.sleep(7200)


def get_cosmos_database():
    client = CosmosClient(cosmos_url, credential=cosmos_key)
    logging.info("conexion base de datos")
    return client.get_database_client(database_name)


def check_if_container_exists(containers):
    logging.info("revisa si hay contenedor")
    return any([True if (container.get('id') == container_name) else False for container in containers])


def create_container(database):
    if (not check_if_container_exists(database.list_containers())):
        partition_key = PartitionKey(path='/id', kind='Hash')
        database.create_container(id=container_name, partition_key=partition_key)
        logging.warning("se crea contenedor")


upload = mp.Process(target=upload_data)
upload.start()

time.sleep(2)

upload_2 = mp.Process(target=upload_data)
upload_2.start()

time.sleep(2)

upload_3 = mp.Process(target=upload_data)
upload_3.start()

time.sleep(2)

download = mp.Process(target=download_data)
download.start()

time.sleep(7200)

cleaner = mp.Process(target=clean_base)
cleaner.start()
