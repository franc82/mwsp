from functools import wraps
from flask import request, Blueprint, render_template, jsonify, session, send_from_directory
from my_app import db, app, mail, stripekey
from my_app.catalog.models import Guest, SettingsForm, WeddingChartPrinter, \
    SeatingPlan, StripeWrapper, ContactForm, ContactMessage
# from sqlalchemy.orm.util import join
from sqlalchemy import desc
import uuid
# import stripe
from datetime import datetime
# import json
import random
from flask_weasyprint import HTML, render_pdf
import networkx as nx
from flask_mail import Message
import sys
# from networkx.algorithms import approximation as approx
# from networkx.readwrite import json_graph

catalog = Blueprint('catalog', __name__)


def template_or_json(template=None):
    """"Return a dict from your view and this will either
    pass it to a template or render json. Use like:

    @template_or_json('template.html')
    """
    def decorated(f):
        @wraps(f)
        def decorated_fn(*args, **kwargs):
            ctx = f(*args, **kwargs)
            if request.is_xhr or not template:
                return jsonify(ctx)
            else:
                return render_template(template, **ctx)
        return decorated_fn
    return decorated


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@catalog.route('/')
#@catalog.route('/home')
#@template_or_json('home.html')
def home():
    Settingform = SettingsForm()
    return render_template('home.html', form=Settingform, title='Welcome to my App')


@catalog.route('/faq')
def faq():
    return render_template('faq.html', title='FAQ')


@catalog.route('/contact', methods=['POST', 'GET'])
def contact():
    contactform = ContactForm()
    if request.method == 'POST':
        message = request.form
        # print('message: ', message.get('message'))
        # print('email: ', message.get('email'))
        # print('name: ', message.get('name'))
        msg = Message('New Contact Message', sender=message.get('email'),
                      recipients=['id1@gmail.com'],
                      body=message.get('message')
                      )

        success = True
        objMessage = ContactMessage(fullname=message.get('name'),
                                    email=message.get('email'),
                                    message=message.get('message'),
                                    ipaddress=request.remote_addr,
                                    useragent=request.headers.get('User-Agent')
                                    )
        db.session.add(objMessage)
        db.session.commit()

        try:
            mail.send(msg)
        except:
            success = False
            for i, e in enumerate(sys.exc_info()):
                print('error %s => %s' % (i, sys.exc_info()[i]))

        return render_template('contact.html', form=contactform, title='Contact Us', success=success)
    elif request.method == 'GET':
        return render_template('contact.html', form=contactform, title='Contact Us')


@catalog.route('/robots.txt')
@catalog.route('/sitemap.xml')
def static_from_root():
    return send_from_directory('', request.path[1:])


@catalog.route('/step2', methods=['GET', 'POST'])
def step2():
    if request.method == 'POST':
        numguest = int(request.form.get('guests'))
        numtables = request.form.get('tables')
        minguestpertable = request.form.get('minguest')
        numguestspertable = request.form.get('guestpertables')
        session['user_id'] = str(uuid.uuid4().hex)
        session['user_agent'] = str(request.headers.get('User-Agent'))
        session['ip'] = str(request.remote_addr)
        session['config'] = {
            'numguest': numguest,
            'numtables': numtables,
            'minguestpertable': minguestpertable,
            'numguestspertable': numguestspertable
        }
        session['guestlist'] = [Guest(i + 1, "Guest " + str(i + 1)) for i in range(numguest)]
        graph = nx.Graph()
        graph.add_edges_from([(int(i['id']), int(i['id'])) for i in session['guestlist']])
        session['graph'] = graph
    return render_template('guestdetails.html', title='Guest Details')


@catalog.route('/step3')
@catalog.route('/step3/<int:page>')
def step3(page=1):
    numguests = len(session['guestlist'])
    guestperpage = 50
    numpages = -(-numguests//guestperpage)
    arrGuestList = session['guestlist'][guestperpage*(page-1):page*guestperpage]
    namelookup = {guest['id']: guest['name'] for guest in arrGuestList}
    friendListLookup = {guest['id']: [namelookup[friendid] for friendid in guest['friends']] for guest in arrGuestList}

    guestconfig = {
        'numtables': session['config']['numtables'],
        'numguestspertable': session['config']['numguestspertable'],
        'hasnext': page < numpages,
        'hasprev': page > 1,
        'prevpagenum': page-1,
        'nextpagenum': page+1,
        'numguests': numguests,
        'gueststartnum': (page-1) * guestperpage,
        'guestendnum': len(arrGuestList),
        'numpages': numpages,
        'friendlookup': friendListLookup,
        'guestlist': [{'id': i['id'], 'name': i['name'], 'acq': i['acq']} for i in arrGuestList]
    }

    #print(session['guestlist'])
    #print('num guests: ', len(session['guestlist']))
    #print(friendListLookup)
    return render_template('guestreview.html', title='Guest Review', guests=guestconfig)


@catalog.route('/results')
def results():
    numguests = int(session['config']['numguest'])
    num_tables = int(session['config']['numtables'])
    table_capacity = int(session['config']['numguestspertable'])
    # min_known_neighbors = 2
    min_known_neighbors = int(session['config']['minguestpertable'])
    names = [i['name'] for i in session['guestlist']]

    # randomly connect non-neighbors
    ''''
    for node in session['graph'].nodes():
        for i in nx.non_neighbors(session['graph'], node):
            session['graph'].add_edge(node, i, weight=random.randint(0, 1))
    '''

    '''
    session['graph'].add_edge(1, 2, weight=50)
    session['graph'].add_edge(3, 4, weight=50)
    session['graph'].add_edge(3, 9, weight=10)
    session['graph'].add_edge(5, 6, weight=50)
    session['graph'].add_edge(7, 8, weight=50)
    session['graph'].add_edge(10, 11, weight=50)
    '''
    # ensure that nodes with the same acquintance are connected with weight 1
    # this operation should happen just before passing the graph to the final computation
    acqlookup = {guest['id']: guest['acq'] for guest in session['guestlist']}

    for node in session['graph'].nodes():
        #print('node %s is in the graph acq is %s' % (node, acqlookup[node]))
        for i in nx.non_neighbors(session['graph'], node):
            #print('acq of node %d is %s vs acq of node %d is %s' % (node, acqlookup[node], i, acqlookup[i]))
            if acqlookup[node] and acqlookup[node] == acqlookup[i]:
                session['graph'].add_edge(node, i, weight=1)

    # check the network connectivity, if it equal to 0 it means that the customer didn't specify
    # any guest acquintance, so we randomly connect the nodes for the solver to work correctly
    if session['graph'].number_of_edges() == session['graph'].number_of_nodes():
        # we need to randomly assign weight to nodes
        print('randomly assigning weights as there are not enough edges')
        for node in session['graph'].nodes():
            for i in nx.non_neighbors(session['graph'], node):
                session['graph'].add_edge(node, i, weight=random.choice([0, 1, 50]))

    C = nx.adjacency_matrix(session['graph'],
                            nodelist=range(1, session['graph'].number_of_nodes() + 1)).todense().tolist()
    #print('matrix: ', C)
    solution = WeddingChartPrinter.solve_with_discrete_model(num_tables, table_capacity, min_known_neighbors, C, names)
    solutionrow = SeatingPlan(session['user_id'], solution, session)
    db.session.add(solutionrow)
    db.session.commit()

    '''
    additionaljs = ["https://js.stripe.com/v3/"]
    stripe.api_key = 'sk_test_4eC39HqLyjWDarjtT1zdp7dc'
    product = stripe.Product.create(
        name='Blue banana',
    )
    price = stripe.Price.create(
        product=product['id'],
        unit_amount=500,
        currency='usd',
    )
    stripe_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': price['id'],
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://example.com/success/%s' % session['user_id'],
        cancel_url='https://example.com/cancel/%s' % session['user_id'],
    )
    '''
    # stripe payment data
    #sapikey = 'sk_test_4eC39HqLyjWDarjtT1zdp7dc'
    #sapikey = 'sk_test_51HDuHyKfKC2ONPsdR2fZjJ6nZEsJ6rGpGiV6s6HNKJjqvch3mhlIqyus6VZjwHw8RnFpEZCNxXbyZaLORP1hSwBw00mV32lWlQ'
    #print('[INFO] Stripe key: ', stripekey)
    stripejs, stripeobj = StripeWrapper.generatePaymentData(session['user_id'], stripekey, request.url_root)
    sol = dict(list(solution.items())[:len(solution)//2])
    return render_template('results.html', title='Results', seating=sol, extrajs=stripejs, stripeobj=stripeobj)


@catalog.route('/cancel/<sessionid>')
def rendercancellationpage(sessionid):
    seatingplan = SeatingPlan.query.filter_by(sessionid=sessionid).first_or_404()
    if seatingplan:
        d1 = seatingplan.solutiondate
        t = datetime.today()
        delta = t - d1
        #print('[INFO] num days = ', delta.days)

    # stripe payment data
    #sapikey = 'sk_test_4eC39HqLyjWDarjtT1zdp7dc'
    stripejs, stripeobj = StripeWrapper.generatePaymentData(sessionid, stripekey, request.url_root)
    sol = seatingplan.solution
    return render_template('cancel.html', seating=dict(list(sol.items())[:len(sol)//2]), title='Cancellation page',
                           extrajs=stripejs, stripeobj=stripeobj
                           )


@catalog.route('/paymentsuccess/<sessionid>', methods=['POST', 'GET'])
def rendersuccesspage(sessionid):
    #sApikey = 'sk_test_4eC39HqLyjWDarjtT1zdp7dc'
    result = StripeWrapper.verifypayment(stripekey, request)
    seatingplan = SeatingPlan.query.filter_by(sessionid=sessionid).first_or_404()

    if result:
        return render_template('paymentsuccess.html', sessionid=sessionid, title='Payment Success page')
    else:
        # render cancel page with an error message
        return render_template('cancel.html', seating=seatingplan.solution, title='Cancellation page')


@catalog.route('/seating_<sessionid>.pdf')
def seatingpdf(sessionid):
    seatingplan = SeatingPlan.query.filter_by(sessionid=sessionid).first_or_404()
    html = render_template('seatingpdf.html', seating=seatingplan.solution)
    return render_pdf(HTML(string=html))


@catalog.route('/guest', methods=['POST'])
@catalog.route('/guest/<int:guestid>', methods=['GET', 'POST'])
def editguest(guestid=None):
    response = {}
    #print('[INFO] in here', guestid)
    if request.method == 'POST':
        # if the guestid is set then we need to update the record otherwise we add a new guest
        if guestid is not None:
            # loop through the guest list in the session and update the record of the corresponding guest
            # data = request.form.get('friends').split(',')
            response = {'message': 'unable to add/update this guest', 'numguests': len(session['guestlist'])}
            # k = request.form.items()

            #for k, v in k:
            #    print('[INFO] passed keys {} value: {}'.format(k, v))

            for idx, guest in enumerate(session['guestlist']):
                #print('[INFO] current guest id: %s type: %s inputguestid: %s' % (guest['id'], type(guest['id']), guestid))
                if guest['id'] == guestid:
                    # update guest and break
                    for key, value in request.form.items():
                        if key == 'friends':
                            #print('value: ', value)
                            if value:
                                # at least one friend was specified
                                friendlist = [int(i) for i in value.split(',')]
                                for innerguest in session['guestlist']:
                                    if innerguest['id'] in friendlist and guestid not in innerguest['friends']:
                                        innerguest['friends'].append(guestid)

                                guest[key] = friendlist
                            else:
                                # no friend was specified for this guest so we need to remove any previously stated
                                for innerguest in session['guestlist']:
                                    if innerguest['id'] == guestid:
                                        innerguest['friends'].clear()
                                    elif guestid in innerguest['friends']:
                                        innerguest['friends'].remove(guestid)

                            # update the graph with data about this node
                            # session['graph'].add_edges_from()
                        elif key != 'guestid':
                            guest[key] = value

                    # update the guest list
                    session['guestlist'][idx] = guest
                    response['message'] = 'Guest successfully updated!'
                    response['numguests'] = len(session['guestlist'])
                    response['updatedrecords'] = guest
                    break

            # update the graph if we are passing a friend list
            if request.form.get('friends'):
                # first remove all the edge from the current node
                for i in list(session['graph'].neighbors(guestid)):
                    if i != guestid:
                        session['graph'].remove_edge(guestid, i)

                # add the new edges with their corresponding weights (50)
                friendlist = [int(i) for i in request.form.get('friends').split(',')]
                session['graph'].add_edges_from([(guestid, i, {'weight': 50}) for i in friendlist])

                # finally for each guest, we check its acquintance and if there's none,
                # then we set it to the current guest
                currentguest = next((guest for guest in session['guestlist'] if guest['id'] == guestid), {})
                currentguestacq = currentguest['acq'] if 'acq' in currentguest else ''

                if currentguestacq:
                    for guest in session['guestlist']:
                        if guest['id'] in friendlist and guest['id'] != guestid and not guest['acq']:
                            # print('setting the acq of guest id %s to %s' % (guest['id'], currentguestacq))
                            guest['acq'] = currentguestacq

            else:
                # no friend was passed so we need to clear the friendlist of this guest
                # as well as all the edges from this node
                for guest in session['guestlist']:
                    if guest['id'] == guestid:
                        # guest found
                        guest['friends'].clear()

                        # clear all edges from this node in the graph
                        for i in list(session['graph'].neighbors(guestid)):
                            if i != guestid:
                                session['graph'].remove_edge(guestid, i)

            response['guestslist'] = session['guestlist']
            #response['graph'] = json_graph.node_link_data(session['graph'])
            #response['matrixC'] = [[1 if i == j else 50 if j == 1 else random.randint(0, 1) for i, guesti in enumerate(session['guestlist'])] for j, guestj in enumerate(session['guestlist'])]

            # ensure that guests belonging to the same acq are connected with 1
            # this operation should happen just before passing the graph to the final computation
            '''
            acqlookup = {guest['id']: guest['acq'] for guest in session['guestlist']}
            for node in session['graph'].nodes():
                print('node %s is in the graph acq is %s' % (node, acqlookup[node]))
                for i in nx.non_neighbors(session['graph'], node):
                    print('acq of node %d is %s vs acq of node %d is %s' % (node, acqlookup[node], i, acqlookup[i]))
                    if acqlookup[node] and acqlookup[node] == acqlookup[i]:
                        session['graph'].add_edge(node, i, weight=1)
            '''

            response['matrixC'] = nx.adjacency_matrix(session['graph'], nodelist=range(1, session['graph'].number_of_nodes() + 1)).todense().tolist()
        else:
            # the guest id wasn't provided so we need to add a new guest
            response = {}
            # find the id of new guest to be added
            newguestid = sorted([int(i['id']) for i in session['guestlist']])[-1] + 1
            newguest = Guest(newguestid, 'Guest %d' % newguestid)

            # add the new guest id to the graph
            session['graph'].add_edge(newguestid, newguestid, weight=1)

            for key, value in request.form.items():
                if key == 'friends':
                    if value:
                        friendlist = [int(i) for i in value.split(',')]
                        newguest['friends'] = friendlist

                        # update those in the graph
                        session['graph'].add_edges_from([(newguestid, i, {'weight': 50}) for i in friendlist])
                    else:
                        print('no friend was provided here')

                else:
                    newguest[key] = value

            session['guestlist'].append(newguest)
            response['guestlist'] = session['guestlist']
            response['matrixC'] = nx.adjacency_matrix(session['graph']).todense().tolist()
    elif request.method == 'GET':
        # get a guest given his/her id of null otherwise
        response['guest'] = next((guest for guest in session['guestlist'] if guest['id'] == guestid), {})
        response['guestlist'] = [{'id': guest['id'], 'name': guest['name']} for guest in session['guestlist'] if guest['id'] != guestid]

    return response


'''
@catalog.route('/add', methods=['POST'])
def addguest():
    response = {}
    # find the id of new guest to be added
    newguestid = sorted([int(i['id']) for i in session['guestlist']])[-1] + 1
    newguest = Guest(newguestid, 'Guest %d' % newguestid)

    # add the new guest id to the graph
    session['graph'].add_edge(newguestid, newguestid, weight=1)

    for key, value in request.form.items():
        if key == 'friends':
            friendlist = [int(i) for i in value.split(',')]
            newguest['friends'] = friendlist

            # update those in the graph
            session['graph'].add_edges_from([(newguestid, i, {'weight': 50}) for i in friendlist])
        else:
            newguest[key] = value

    session['guestlist'].append(newguest)
    response['guestlist'] = session['guestlist']
    response['matrixC'] = nx.adjacency_matrix(session['graph']).todense().tolist()

    return response
'''


@catalog.route('/delete/<int:guestid>', methods=['POST'])
def deleteguest(guestid):
    response = {'message': 'unable to remove this guest', 'numguests': len(session['guestlist'])}
    for i in session['guestlist']:
        print('guest id: %s num friends %d' % (i['id'], len(i['friends'])))

    for guest in session['guestlist']:
        if guest['id'] == guestid:
            print('found key')
            session['guestlist'].remove(guest)
            response['message'] = 'guest successful removed current length %d' % (len(session['guestlist']))
            break

    # next remove this guest from the other guest's friend
    for guest in session['guestlist']:
        if guestid in guest['friends']:
            guest['friends'].remove(guestid)

    # remove the node from the graph too
    session['graph'].remove_node(guestid)
    response['numguests'] = len(session['guestlist'])
    response['guests'] = session['guestlist']
    response['matrixC'] = nx.adjacency_matrix(session['graph']).todense().tolist()

    return response


@catalog.route('/sp')
@catalog.route('/sp/<int:page>')
def adminres(page=1):
    res = SeatingPlan.query.order_by(desc(SeatingPlan.solutiondate)).paginate(page, 10)
    num = len(SeatingPlan.query.all())
    return render_template('seatingplans.html', seatingplans=res, title='seating plans', total=num)


''''
@catalog.route('/product/<id>')
def product(id):
    product = Product.query.get_or_404(id)
    return render_template('product.html', product=product)


@catalog.route('/products')
@catalog.route('/products/<int:page>')
def products(page=1):
    products = Product.query.paginate(page, 10)
    return render_template('products.html', products=products)


@catalog.route('/product-create', methods=['GET', 'POST'])
def create_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        categ_name = request.form.get('category')
        category = Category.query.filter_by(name=categ_name).first()
        if not category:
            category = Category(categ_name)
        product = Product(name, price, category)
        db.session.add(product)
        db.session.commit()
        flash('The product %s has been created' % name, 'success')
        return redirect(url_for('catalog.product', id=product.id))
    return render_template('product-create.html')


@catalog.route('/product-search')
@catalog.route('/product-search/<int:page>')
def product_search(page=1):
    name = request.args.get('name')
    price = request.args.get('price')
    company = request.args.get('company')
    category = request.args.get('category')
    products = Product.query
    if name:
        products = products.filter(Product.name.like('%' + name + '%'))
    if price:
        products = products.filter(Product.price == price)
    if company:
        products = products.filter(Product.company.like('%' + company + '%'))
    if category:
        products = products.select_from(join(Product, Category)).filter(
            Category.name.like('%' + category + '%')
        )
    return render_template(
        'products.html', products=products.paginate(page, 10)
    )


@catalog.route('/category-create', methods=['POST',])
def create_category():
    name = request.form.get('name')
    category = Category(name)
    db.session.add(category)
    db.session.commit()
    return render_template('category.html', category=category)


@catalog.route('/category/<id>')
def category(id):
    category = Category.query.get_or_404(id)
    return render_template('category.html', category=category)


@catalog.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)
'''