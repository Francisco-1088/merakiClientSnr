import meraki.aio
import asyncio
import pandas as pd

api_key = "YOUR_API_KEY"
org_id = "YOUR_ORG_ID"
timespan = 432000 # In seconds, set to 5 days = 432000

aiomeraki = meraki.aio.AsyncDashboardAPI(api_key,
            base_url="https://api.meraki.com/api/v1",
            log_file_prefix=__file__[:-3],
            print_console=True,
            maximum_retries=200,
            maximum_concurrent_requests=10,
)

async def get_client_snr(aiomeraki, net_id, net_name, client):
    snr_history = await aiomeraki.wireless.getNetworkWirelessSignalQualityHistory(networkId=net_id, clientId=client['id'])
    return net_id, net_name, client, snr_history

async def get_net_clients(aiomeraki, net_id, net_name):
    clients = await aiomeraki.networks.getNetworkClients(networkId=net_id, timespan=timespan,recentDeviceConnections='Wireless', total_pages=-1)
    return net_id, net_name, clients

async def gather_net_clients(nets):
    net_tasks = []
    client_tasks = []
    for net in nets:
        net_tasks.append(get_net_clients(aiomeraki, net['id'], net['name']))
    print("net_tasks", len(net_tasks))

    for net_task in asyncio.as_completed(net_tasks):
        net_id, net_name, clients = await net_task
        print(net_name, len(clients))
        for client in clients:
            client_tasks.append(get_client_snr(aiomeraki, net_id, net_name, client))
    print("client_tasks", len(client_tasks))
    client_details = []
    for client_task in asyncio.as_completed(client_tasks):
        net_id, net_name, client, snr_history = await client_task
        client_details.append({"net_id": net_id, "net_name": net_name, "client_name": client["description"], "client_id": client["id"], "client_mac": client["mac"], "snr_history": snr_history})
    return client_details

async def main(aiomeraki):
    async with aiomeraki:
        networks = await aiomeraki.organizations.getOrganizationNetworks(org_id, total_pages=-1)
        nets = [net for net in networks if 'wireless' in net['productTypes']]
        print("nets", len(nets))
        client_details = await gather_net_clients(nets)
    return client_details

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    client_details = loop.run_until_complete(main(aiomeraki))
    client_details_df = pd.DataFrame(client_details)
    client_details_df.to_csv("client_details.csv")
