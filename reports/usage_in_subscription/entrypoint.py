from cnct import R
from reports.utils import convert_to_datetime, get_value, get_basic_value, Progress
from concurrent import futures


def get_record(client, asset, start_date, end_date, progress):
    billable_status = ['approved', 'closed']
    rql = R().asset.id.eq(asset['id']) & R().status.oneof(billable_status) & (
        (
            R().start_date.ge(f'{start_date}') & R().start_date.lt(f'{end_date}')
        ) | (
            R().end_date.ge(f'{start_date}') & R().end_date.lt(f'{end_date}')
        )
    )
    usage_records = client.ns('usage').records.filter(rql)
    uf = []
    for record in usage_records:
        if record['usagefile']['id'] not in uf:
            uf.append(record['usagefile']['id'])
    progress.increment()
    return [
        get_basic_value(asset, 'id'),
        get_basic_value(asset, 'external_id'),
        get_basic_value(asset, 'status'),
        convert_to_datetime(asset['events']['created']['at']),
        convert_to_datetime(asset['events']['updated']['at']),
        get_value(asset['tiers'], 'customer', 'id'),
        get_value(asset['tiers'], 'customer', 'name'),
        get_value(asset['tiers'], 'customer', 'external_id'),
        get_value(asset['tiers'], 'tier1', 'id'),
        get_value(asset['tiers'], 'tier1', 'name'),
        get_value(asset['tiers'], 'tier1', 'external_id'),
        get_value(asset['tiers'], 'tier2', 'id'),
        get_value(asset['tiers'], 'tier2', 'name'),
        get_value(asset['tiers'], 'tier2', 'external_id'),
        get_value(asset['connection'], 'provider', 'id'),
        get_value(asset['connection'], 'provider', 'name'),
        get_value(asset['connection'], 'vendor', 'id'),
        get_value(asset['connection'], 'vendor', 'name'),
        get_value(asset, 'product', 'id'),
        get_value(asset, 'product', 'name'),
        get_value(asset['connection'], 'hub', 'id'),
        get_value(asset['connection'], 'hub', 'name'),
        len(uf),
        ', '.join(uf)
    ]


def generate(client, parameters, progress_callback):
    product_rql = R().status.eq('active')

    if parameters.get('product') and parameters['product']['all'] is False:
        product_rql &= R().product.id.oneof(parameters['product']['choices'])

    assets = client.ns('subscriptions').assets.filter(product_rql)

    total = assets.count()
    progress = Progress(progress_callback, total)
    start_date = parameters['period']['after']
    end_date = parameters['period']['before']

    ex = futures.ThreadPoolExecutor(max_workers=10)

    wait_for = []
    for asset in assets:
        wait_for.append(
            ex.submit(
                get_record,
                client,
                asset,
                start_date,
                end_date,
                progress
            )
        )
    for future in futures.as_completed(wait_for):
        yield future.result()
