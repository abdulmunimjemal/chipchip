# File: data/generate_sample_data_poc.py
import clickhouse_connect
from faker import Faker
import random
import uuid
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

env_path_options = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), # if script in data/, .env in root
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', '.env') # if script in data/, .env in src/
]
dotenv_path = next((path for path in env_path_options if os.path.exists(path)), None)

if dotenv_path:
    load_dotenv(dotenv_path)
    print(f"Loaded .env from {dotenv_path}")
else:
    print("Warning: .env file not found in expected locations. Using defaults or environment variables if set elsewhere.")

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123)) # HTTP port
CLICKHOUSE_USERNAME = os.getenv("CLICKHOUSE_USERNAME", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "chipchip_db") # Ensure this DB exists

NUM_USERS = 200
NUM_CATEGORIES = 5
NUM_PRODUCTS_PER_CATEGORY = 10
NUM_ORDERS = 1000
NUM_GROUP_DEALS = 30
NUM_GROUPS_PER_DEAL = 2 # Max groups initiated per deal
MAX_MEMBERS_PER_GROUP = 15

# Date range for data generation
DATE_START = datetime(2024, 1, 1)
DATE_END = datetime(2024, 8, 31)

fake = Faker()

def get_db_client():
    print(f"Connecting to ClickHouse: {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}, DB: {CLICKHOUSE_DATABASE}, User: {CLICKHOUSE_USERNAME}")
    try:
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            username=CLICKHOUSE_USERNAME,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DATABASE,
            secure=False # Set to True if using TLS/HTTPS
        )
        print("Successfully connected to ClickHouse.")
        return client
    except Exception as e:
        print(f"Failed to connect to ClickHouse: {e}")
        raise

def clear_poc_tables(client):
    # Order matters due to potential (unenforced in CH by default) FKs logic
    tables = [
        "group_members_poc", "order_items_poc", "orders_poc",
        "groups_poc", "group_deals_poc",
        "products_poc", "categories_poc", "users_poc"
    ]
    for table in tables:
        try:
            print(f"Clearing table {table}...")
            client.command(f"TRUNCATE TABLE IF EXISTS {table}")
        except Exception as e:
            print(f"Error truncating table {table}: {e}")
    print("PoC tables cleared (or attempted).")

def create_poc_tables(client):
    """
    Ensure PoC schema exists by executing DDL from create_tables_poc.sql
    """
    import os
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'create_tables_poc.sql')
    with open(sql_path, 'r') as f:
        ddl = f.read()
    for stmt in ddl.split(';'):
        stmt = stmt.strip()
        if not stmt:
            continue
        try:
            client.command(stmt)
        except Exception:
            # ignore existing or invalid statements
            pass
    print("Ensured PoC tables exist.")

def insert_data(client, table_name, records):
    """
    Inserts list of dict records into ClickHouse by converting to rows and columns.
    """
    if not records:
        return
    columns = list(records[0].keys())
    rows = [[r[col] for col in columns] for r in records]
    client.insert(table_name, rows, column_names=columns)

def generate_users_poc(client, num_users):
    users_data = []
    user_ids = []
    reg_channels = ['organic', 'referral', 'paid_ad_facebook', 'paid_ad_influencer', 'paid_ad_google']
    cust_segments = ['Working Professionals', 'Students', 'Home Makers', 'Tech Savvy', 'Budget Shoppers']

    for i in range(num_users):
        user_id = str(uuid.uuid4())
        user_ids.append(user_id)
        created_at = fake.date_time_between(start_date=DATE_START, end_date=DATE_END, tzinfo=None)
        # Ensure registration_date for July retention test
        if i < num_users * 0.15 : # 15% users register in July
             created_at = fake.date_time_between(start_date=datetime(2024,7,1), end_date=datetime(2024,7,31), tzinfo=None)

        users_data.append({
            'user_id': user_id,
            'name': fake.name(),
            'email': fake.email(),
            'registration_date': created_at,
            'user_status': random.choice(['active', 'inactive', 'pending']),
            'is_group_leader': True if i < num_users * 0.1 else random.choice([True, False, False, False]), # ~25-30% group leaders
            'registration_channel': random.choice(reg_channels),
            'customer_segment': random.choice(cust_segments)
        })
    if users_data:
        insert_data(client, 'users_poc', users_data)
    print(f"Generated {len(users_data)} users for users_poc.")
    return user_ids

def generate_categories_poc(client, num_categories):
    categories_data = []
    category_ids = []
    base_categories = ['Fresh Produce', 'Dairy & Eggs', 'Bakery', 'Pantry Staples', 'Beverages', 'Snacks', 'Frozen Foods']
    selected_categories = random.sample(base_categories, min(num_categories, len(base_categories)))
    if 'Fresh Produce' not in selected_categories and num_categories > 0: # Ensure 'Fresh Produce' for Q3
        selected_categories[0] = 'Fresh Produce'


    for name in selected_categories:
        cat_id = str(uuid.uuid4())
        category_ids.append(cat_id)
        categories_data.append({'category_id': cat_id, 'category_name': name})

    if categories_data:
        insert_data(client, 'categories_poc', categories_data)
    print(f"Generated {len(categories_data)} categories for categories_poc.")
    return categories_data # list of dicts

def generate_products_poc(client, categories_data, num_products_per_category):
    products_data = []
    product_ids = []
    for cat_info in categories_data:
        for _ in range(num_products_per_category):
            prod_id = str(uuid.uuid4())
            product_ids.append(prod_id)
            products_data.append({
                'product_id': prod_id,
                'product_name': f"{cat_info['category_name']} Item {fake.word().capitalize()}",
                'category_name': cat_info['category_name'],
                'status': 'active',
                'original_price': round(random.uniform(1.0, 100.0), 2)
            })
    if products_data:
        insert_data(client, 'products_poc', products_data)
    print(f"Generated {len(products_data)} products for products_poc.")
    return product_ids

def generate_orders_poc(client, user_ids, num_orders):
    orders_data = []
    order_ids = []
    acq_channels = ['organic', 'influencer_campaign_A', 'facebook_ad_B', 'referral', 'direct', 'email_marketing']
    order_statuses = ['completed', 'pending', 'shipped', 'delivered', 'cancelled']

    for i in range(num_orders):
        order_id = str(uuid.uuid4())
        order_ids.append(order_id)
        user_id = random.choice(user_ids)
        order_date = fake.date_time_between(start_date=DATE_START, end_date=DATE_END, tzinfo=None)

        # Ensure orders in specific months for queries
        if i < num_orders * 0.1: # ~10% orders in May 2024
            order_date = fake.date_time_between(start_date=datetime(2024,5,1), end_date=datetime(2024,5,31,23,59,59))
        elif i < num_orders * 0.2: # ~10% orders in June 2024
            order_date = fake.date_time_between(start_date=datetime(2024,6,1), end_date=datetime(2024,6,30,23,59,59))
        elif i < num_orders * 0.3: # ~10% orders in August 2024
            order_date = fake.date_time_between(start_date=datetime(2024,8,1), end_date=datetime(2024,8,31,23,59,59))


        orders_data.append({
            'order_id': order_id,
            'user_id': user_id,
            'status': random.choice(order_statuses),
            'total_amount': 0.0, # Will be updated after order_items
            'order_date': order_date,
            'payment_method': random.choice(['credit_card', 'paypal', 'telebirr', 'cbe_birr']),
            'acquisition_channel': random.choice(acq_channels)
        })
    if orders_data:
        # Insert with placeholder total_amount
        insert_data(client, 'orders_poc', orders_data)
    print(f"Generated {len(orders_data)} orders for orders_poc (total_amount pending).")
    return orders_data # list of dicts, for later update

def generate_order_items_poc(client, orders_data_list, product_ids):
    order_items_data = []
    updated_orders_totals = {} # Store order_id: total_amount

    for order_dict in orders_data_list:
        order_id = order_dict['order_id']
        num_items_in_order = random.randint(1, 5)
        current_order_total = 0.0

        for _ in range(num_items_in_order):
            product_id = random.choice(product_ids)
            # Fetch product price (in a real scenario, join or pre-fetch; here, use random or placeholder)
            # For PoC, let's get it from products_poc table if possible, or use random
            # This is slow, better to fetch all product prices once.
            # For simplicity now:
            product_info = client.query_df(f"SELECT original_price, product_name, category_name FROM products_poc WHERE product_id = '{product_id}' LIMIT 1")

            if not product_info.empty:
                price_per_unit = float(product_info['original_price'].iloc[0])
                 # For Q3 (fresh produce sales in August), ensure some fresh produce are ordered in August
                if order_dict['order_date'].month == 8 and product_info['category_name'].iloc[0] == 'Fresh Produce':
                    quantity = random.randint(1, 5) # Higher quantity for featured items
                else:
                    quantity = random.randint(1, 3)
            else: # Fallback if product not found (should not happen with good data gen)
                price_per_unit = round(random.uniform(5.0, 50.0), 2)
                quantity = random.randint(1, 3)

            order_items_data.append({
                'order_item_id': str(uuid.uuid4()),
                'order_id': order_id,
                'product_id': product_id,
                'quantity': quantity,
                'price_per_unit': price_per_unit
            })
            current_order_total += quantity * price_per_unit
        updated_orders_totals[order_id] = round(current_order_total, 2)

    if order_items_data:
        insert_data(client, 'order_items_poc', order_items_data)
    print(f"Generated {len(order_items_data)} order items for order_items_poc.")

    # Update total_amount in orders_poc
    # This is inefficient for large data. In ClickHouse, updates are mutations.
    # A better way for bulk updates is to re-insert or use background mutations.
    # For PoC data gen, this might be acceptable if slow.
    print("Updating total_amount in orders_poc...")
    for order_id, total in updated_orders_totals.items():
        try:
            # ClickHouse `ALTER TABLE ... UPDATE` is a heavy operation.
            # For a PoC, if this is too slow, consider re-generating orders with correct totals,
            # or accept that totals might be 0 for this script.
            # A common pattern is to insert into a temporary table then rename, or use ReplacingMergeTree.
            # For this script, we'll try the ALTER UPDATE.
            # Ensure `allow_experimental_lightweight_delete` or `allow_experimental_alter_materialized_view_structure` might be needed depending on version/setup.
            # However, a simple UPDATE is standard.
            client.command(f"ALTER TABLE orders_poc UPDATE total_amount = {total} WHERE order_id = '{order_id}'")
        except Exception as e:
            print(f"Warning: Could not update total_amount for order {order_id}: {e}. Totals might remain 0.0 for some orders.")
    print("Finished attempting to update order totals.")


def generate_group_deals_poc(client, product_ids, num_deals):
    group_deals_data = []
    for _ in range(num_deals):
        prod_id = random.choice(product_ids)
        base_price_df = client.query_df(f"SELECT original_price FROM products_poc WHERE product_id = '{prod_id}' LIMIT 1")
        base_price = float(base_price_df['original_price'].iloc[0]) if not base_price_df.empty else random.uniform(10, 200)

        eff_from = fake.date_time_between(start_date=DATE_START, end_date=DATE_END - timedelta(days=10))
        eff_to = eff_from + timedelta(days=random.randint(7, 30)) if random.choice([True, False]) else None

        group_deals_data.append({
            'group_deal_id': str(uuid.uuid4()),
            'product_id': prod_id,
            'group_price': round(base_price * random.uniform(0.7, 0.9), 2), # Discounted
            'max_group_member': random.randint(5, MAX_MEMBERS_PER_GROUP),
            'effective_from': eff_from,
            'effective_to': eff_to,
            'status': 'active' if (eff_to is None or eff_to > datetime.now()) else 'expired'
        })
    if group_deals_data:
        insert_data(client, 'group_deals_poc', group_deals_data)
    print(f"Generated {len(group_deals_data)} group deals.")
    return group_deals_data # list of dicts


def generate_groups_and_members_poc(client, group_deals_list, user_ids_all, orders_list):
    groups_data = []
    group_members_data = []
    
    all_users_df = client.query_df("SELECT user_id, is_group_leader FROM users_poc")
    group_leader_ids = all_users_df[all_users_df['is_group_leader'] == True]['user_id'].tolist()
    
    if not group_leader_ids:
        print("Warning: No group leaders found. Cannot generate groups or group members.")
        return

    for deal in group_deals_list:
        if deal['status'] != 'active': # Only create groups for active deals
            continue
        for _ in range(random.randint(1, NUM_GROUPS_PER_DEAL)): # Multiple groups can be started for the same deal
            group_id = str(uuid.uuid4())
            leader_id = random.choice(group_leader_ids)
            group_status = random.choice(['active', 'active', 'completed', 'failed']) # Bias towards active/completed
            group_created_at = fake.date_time_between(start_date=deal['effective_from'], end_date=deal['effective_to'] or DATE_END)
            
            # Ensure created_at for Q8 (May)
            if random.random() < 0.3: # 30% chance group created in May
                 group_created_at = fake.date_time_between(start_date=datetime(2024,5,1), end_date=datetime(2024,5,31))


            groups_data.append({
                'group_id': group_id,
                'group_deal_id': deal['group_deal_id'],
                'group_leader_id': leader_id,
                'status': group_status,
                'created_at': group_created_at
            })

            # Generate members for this group
            num_members = random.randint(1, deal['max_group_member'])
            # Ensure leader is a member (can be implicit if they also "join")
            # For simplicity, members are other users.
            potential_members = [uid for uid in user_ids_all if uid != leader_id]
            if not potential_members: continue

            # For Q4 (first time purchasing customers through group buys) & Q8 (products from completed group buys)
            linked_order_for_member = None
            # Prepare list for linking completed orders
            completed_orders_for_linking = []
            if group_status == 'completed':
                # Find a completed order to link, preferably for the product in this group deal
                # This is a simplification for PoC data.
                # Find an order associated with the user for the product of the group deal around the group end time.
                # For this script, we'll pick a random existing "completed" order for a member.
                # This is not perfectly realistic but helps create linkable data.
                
                # Find "completed" orders to pick from for linking
                completed_orders_for_linking = [o for o in orders_list if o['status'] == 'completed' and o['order_date'] >= group_created_at]

            for _ in range(num_members):
                if not potential_members: break
                member_user_id = random.choice(potential_members)
                potential_members.remove(member_user_id) # avoid duplicate members in same group for simplicity

                linked_order_for_member = None
                if group_status == 'completed' and completed_orders_for_linking:
                    # Try to find an order for this member
                    member_orders = [o['order_id'] for o in completed_orders_for_linking if o['user_id'] == member_user_id]
                    if member_orders:
                        linked_order_for_member = random.choice(member_orders)
                    elif random.random() < 0.3: # 30% chance a random completed order is linked (not necessarily this user's)
                        linked_order_for_member = random.choice([o['order_id'] for o in completed_orders_for_linking])


                group_members_data.append({
                    'group_member_id': str(uuid.uuid4()),
                    'group_id': group_id,
                    'user_id': member_user_id,
                    'joined_at': fake.date_time_between(start_date=group_created_at, end_date=group_created_at + timedelta(days=3)),
                    'linked_order_id': linked_order_for_member
                })
    
    if groups_data:
        insert_data(client, 'groups_poc', groups_data)
    print(f"Generated {len(groups_data)} groups.")
    if group_members_data:
        insert_data(client, 'group_members_poc', group_members_data)
    print(f"Generated {len(group_members_data)} group members.")


def main():
    client = None
    try:
        client = get_db_client()
        # Create tables if missing, then clear
        create_poc_tables(client)
        clear_poc_tables(client)

        print("\n--- Starting Data Generation ---")
        user_ids_list = generate_users_poc(client, NUM_USERS)
        categories_list_of_dicts = generate_categories_poc(client, NUM_CATEGORIES)
        product_ids_list = generate_products_poc(client, categories_list_of_dicts, NUM_PRODUCTS_PER_CATEGORY)

        # Generate orders first, then items, then update order totals
        orders_list_of_dicts = generate_orders_poc(client, user_ids_list, NUM_ORDERS)
        if orders_list_of_dicts and product_ids_list : # Check if product_ids_list is not empty
             generate_order_items_poc(client, orders_list_of_dicts, product_ids_list)
        else:
            print("Skipping order items generation due to missing orders or products.")


        # Group buys
        group_deals_list_of_dicts = generate_group_deals_poc(client, product_ids_list, NUM_GROUP_DEALS)
        # Ensure orders_list_of_dicts is populated before passing
        # Fetch latest orders_list if totals were updated outside the list variable.
        # For simplicity, we'll pass the initial list; linked_order_id logic will use it.
        updated_orders_list_df = client.query_df("SELECT order_id, user_id, status, order_date FROM orders_poc")
        updated_orders_list = updated_orders_list_df.to_dict('records')

        if group_deals_list_of_dicts and user_ids_list and updated_orders_list:
            generate_groups_and_members_poc(client, group_deals_list_of_dicts, user_ids_list, updated_orders_list)
        else:
            print("Skipping groups and members generation due to missing prerequisite data.")


        print("\n--- Data Generation Complete ---")

    except Exception as e:
        print(f"An error occurred during data generation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()