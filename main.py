from flask import Flask, render_template, request
from sqlalchemy import Column, Integer, String, Numeric, create_engine, text

app = Flask(__name__)
conn_str = "mysql://root:cset155@localhost/boats_db"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()


# render a file
@app.route('/')
def index():
    return render_template('index.html')


# remember how to take user inputs?
@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


# get all boats
# this is done to handle requests for two routes -
@app.route('/boats/')
@app.route('/boats/<page>')
def get_boats(page=1):
    page = int(page)  # request params always come as strings. So type conversion is necessary.
    per_page = 10  # records to show per page

    order_by = request.args.get('order_by', 'id')
    direction = request.args.get('direction', 'asc')
    boat_type = request.args.get('type', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')

    allowed_columns = {
        'id': 'id',
        'name': 'name',
        'price': 'rental_price'
    }
    allowed_directions = {'asc', 'desc'}

    if order_by not in allowed_columns:
        order_by = 'id'
    if direction not in allowed_directions:
        direction = 'asc'

    filters = []
    params = {}

    if boat_type:
        filters.append('type = :type')
        params['type'] = boat_type

    if min_price:
        try:
            params['min_price'] = float(min_price)
            filters.append('rental_price >= :min_price')
        except ValueError:
            min_price = ''

    if max_price:
        try:
            params['max_price'] = float(max_price)
            filters.append('rental_price <= :max_price')
        except ValueError:
            max_price = ''

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ''
    order_clause = f"ORDER BY {allowed_columns[order_by]} {direction.upper()}"
    offset = (page - 1) * per_page
    sql = f"SELECT * FROM boats {where_clause} {order_clause} LIMIT :limit OFFSET :offset"
    params.update({'limit': per_page, 'offset': offset})
    boats = conn.execute(text(sql), params).all()

    filter_params = []
    if boat_type:
        filter_params.append(f"type={boat_type}")
    if min_price:
        filter_params.append(f"min_price={min_price}")
    if max_price:
        filter_params.append(f"max_price={max_price}")

    sort_params = [f"order_by={order_by}", f"direction={direction}"]
    filters_query = '&'.join(filter_params)
    base_query = '&'.join(filter_params + sort_params)

    print(boats)
    return render_template('boats.html', boats=boats, page=page, per_page=per_page,
                           order_by=order_by, direction=direction, base_query=base_query,
                           filters_query=filters_query, boat_type=boat_type,
                           min_price=min_price, max_price=max_price)

def filter_boats(boats, boat_type=None, max_price=None):
    if boat_type:
        boats = [boat for boat in boats if boat.type == boat_type]
    if max_price is not None:
        boats = [boat for boat in boats if boat.rental_price <= max_price]
    return boats


@app.route('/boat/<int:boat_id>')
def boat_detail(boat_id):
    boat = conn.execute(text("SELECT * FROM boats WHERE id = :id"), {"id": boat_id}).first()
    if not boat:
        return render_template('boat_detail.html', boat=None, error='Boat not found.')
    return render_template('boat_detail.html', boat=boat, error=None)


@app.route('/create', methods=['GET'])
def create_get_request():
    return render_template('boats_create.html')


@app.route('/create', methods=['POST'])
def create_boat():
    # you can access the values with request.from.name
    # this name is the value of the name attribute in HTML form's input element
    # ex: print(request.form['id'])
    try:
        conn.execute(
            text("INSERT INTO boats values (:id, :name, :type, :owner_id, :rental_price)"),
            request.form
        )
        return render_template('boats_create.html', error=None, success="Data inserted successfully!")
    except Exception as e:
        error = e.orig.args[1]
        print(error)
        return render_template('boats_create.html', error=error, success=None)

@app.route('/search', methods=['GET'])
def search_boats():
    return render_template('boats_search.html', boats=None, error=None, success=None)

@app.route('/search', methods=['POST'])
def search_boats_request():
    form = request.form
    filters = []
    params = {}

    if form.get('id'):
        filters.append('id = :id')
        params['id'] = int(form['id'])

    if form.get('name'):
        filters.append('name LIKE :name')
        params['name'] = f"%{form['name']}%"

    if form.get('type'):
        filters.append('type LIKE :type')
        params['type'] = f"%{form['type']}%"

    if form.get('owner_id'):
        filters.append('owner_id = :owner_id')
        params['owner_id'] = int(form['owner_id'])

    if form.get('rental_price'):
        filters.append('rental_price = :rental_price')
        params['rental_price'] = float(form['rental_price'])

    if not filters:
        return render_template('boats_search.html', boats=None, error='Enter at least one search value.', success=None)

    query = 'SELECT * FROM boats WHERE ' + ' AND '.join(filters)
    boats = conn.execute(text(query), params).all()

    if not boats:
        return render_template('boats_search.html', boats=[], error='No boats found matching your search.', success=None)

    return render_template('boats_search.html', boats=boats, error=None, success=f'Found {len(boats)} boat(s).')


@app.route('/delete', methods=['POST'])
def delete_boat():
    boat_id = request.form.get('delete_id')
    if not boat_id:
        return render_template('boats_search.html', boats=None, error='No boat ID specified for deletion.', success=None)

    try:
        boat_id = int(boat_id)
    except ValueError:
        return render_template('boats_search.html', boats=None, error='Invalid boat ID.', success=None)

    boat = conn.execute(text('SELECT * FROM boats WHERE id = :id'), {'id': boat_id}).first()
    if not boat:
        return render_template('boats_search.html', boats=None, error='Boat not found.', success=None)

    conn.execute(text('DELETE FROM boats WHERE id = :id'), {'id': boat_id})
    return render_template('boats_search.html', boats=None, error=None, success=f'Boat {boat_id} deleted successfully.')


@app.route('/update', methods=['GET'])
def update_boat_get():
    return render_template('boats_update.html', boat=None, error=None, success=None)


@app.route('/update', methods=['POST'])
def update_boat_post():
    form = request.form
    if not form.get('id'):
        return render_template('boats_update.html', boat=None, error='Boat ID is required.', success=None)

    try:
        boat_id = int(form['id'])
    except ValueError:
        return render_template('boats_update.html', boat=None, error='Boat ID must be a number.', success=None)

    boat = conn.execute(text('SELECT * FROM boats WHERE id = :id'), {'id': boat_id}).first()
    if not boat:
        return render_template('boats_update.html', boat=None, error='Boat not found.', success=None)

    updates = []
    params = {'id': boat_id}

    if form.get('name'):
        updates.append('name = :name')
        params['name'] = form['name']

    if form.get('type'):
        updates.append('type = :type')
        params['type'] = form['type']

    if form.get('owner_id'):
        try:
            params['owner_id'] = int(form['owner_id'])
            updates.append('owner_id = :owner_id')
        except ValueError:
            return render_template('boats_update.html', boat=boat, error='Owner ID must be a number.', success=None)

    if form.get('rental_price'):
        try:
            params['rental_price'] = float(form['rental_price'])
            updates.append('rental_price = :rental_price')
        except ValueError:
            return render_template('boats_update.html', boat=boat, error='Rental price must be numeric.', success=None)

    if not updates:
        return render_template('boats_update.html', boat=boat, error='Enter at least one field to update.', success=None)

    sql = 'UPDATE boats SET ' + ', '.join(updates) + ' WHERE id = :id'
    conn.execute(text(sql), params)
    updated_boat = conn.execute(text('SELECT * FROM boats WHERE id = :id'), {'id': boat_id}).first()

    return render_template('boats_update.html', boat=updated_boat, error=None, success='Boat updated successfully.')


if __name__ == '__main__':
    app.run(debug=True)
