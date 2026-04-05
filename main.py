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
    boats = conn.execute(text(f"SELECT * FROM boats LIMIT {per_page} OFFSET {(page - 1) * per_page}")).all()
    print(boats)
    return render_template('boats.html', boats=boats, page=page, per_page=per_page)


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

if __name__ == '__main__':
    app.run(debug=True)
