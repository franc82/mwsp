from functools import wraps
from flask import request, Blueprint, render_template, jsonify, session, make_response
from my_app import db, app, mail, stripekey
from my_app.catalog.models import Guest, SettingsForm, WeddingChartPrinter, \
    SeatingPlan, StripeWrapper, ContactForm, ContactMessage
# from sqlalchemy.orm.util import join
from sqlalchemy import desc
import uuid
# import stripe
from datetime import datetime, timedelta
# import json
import random
from flask_weasyprint import HTML, render_pdf
import networkx as nx
from flask_mail import Message
import sys
import time
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
    sPageTitle = '404 Not found - MyWeddingSeatingPlanner.com'
    sDescription = 'Sorry the page you are requesting does not exist.'
    objMeta = {
        'googlebot': 'noindex,nofollow',
        'description': sDescription,
        'keywords': 'contact us, wedding, email, contact form',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }
    return render_template('404.html', title=sPageTitle, meta=objMeta), 404


@catalog.route('/')
#@catalog.route('/home')
#@template_or_json('home.html')
def home():
    Settingform = SettingsForm()
    sPageTitle = 'Welcome to your online wedding seating planner tool - MyWeddingSeatingPlanner.com'
    sDescription = 'This website takes the pain from you by helping you to plan the seating of your guests for your wedding in a smart way. Trusted by millions and very reliable.'
    objMeta = {
        'googlebot': 'index,follow,snippet,archive',
        'description': sDescription,
        'keywords': 'wedding seating planner, wedding, planning, online planner, seat',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }
    return render_template('home.html', form=Settingform, meta=objMeta,
                           title=sPageTitle)


@catalog.route('/faq')
def faq():
    sPageTitle = 'FAQ - MyWeddingSeatingPlanner.com'
    sDescription = 'Frequently asked questions about the website. We will answer any of your query in a timely manner.'
    objMeta = {
        'googlebot': 'index,follow,snippet,archive',
        'description': sDescription,
        'keywords': 'FAQ, frequently asked questions, wedding, seating, planning',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }
    return render_template('faq.html', meta=objMeta,
                           title=sPageTitle)


@catalog.route('/contact', methods=['POST', 'GET'])
def contact():
    contactform = ContactForm()
    sPageTitle = 'Contact Us - MyWeddingSeatingPlanner.com'
    sDescription = 'Submit any of your query to us in this page. We usually reply within hours.'
    objMeta = {
        'googlebot': 'index,follow,snippet,archive',
        'description': sDescription,
        'keywords': 'contact us, wedding, email, contact form',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }
    if request.method == 'POST':
        message = request.form
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
            # mail.send(msg)
            print('sending email')
        except:
            success = False
            for i, e in enumerate(sys.exc_info()):
                print('error %s => %s' % (i, sys.exc_info()[i]))

        return render_template('contact.html', meta=objMeta,
                               form=contactform, title=sPageTitle, success=success)
    elif request.method == 'GET':
        return render_template('contact.html', meta=objMeta,
                               form=contactform, title=sPageTitle)


#@catalog.route('/robots.txt')
#@catalog.route('/sitemap.xml')
#def static_from_root():
#    return send_from_directory('', request.path[1:])
# sitemap generation
@catalog.route('/sitemap.xml')
def sitemap():
    pages = ['contact', 'faq', 'demo']
    lastmod = datetime.now() - timedelta(days=10)
    lastmod = lastmod.strftime('%Y-%m-%d')
    parameters = []
    # adding the homepage
    parameters.append({
        'url': request.host_url,
        'modified': lastmod
    })
    for page in pages:
        parameters.append({
            'url': request.host_url + page,
            'modified': lastmod
        })

    xml_sitemap = render_template("sitemap.xml", pages=parameters)
    response = make_response(xml_sitemap)
    response.headers["Content-Type"] = "application/xml"
    return response


@catalog.route('/step2', methods=['GET', 'POST'])
def step2():
    sPageTitle = 'Provide your Guest Details - MyWeddingSeatingPlanner.com'
    sDescription = 'Provide your guest details to the system. we can either do so by uploading a csv file or enter it manually.'
    objMeta = {
        'googlebot': 'index,follow,snippet,archive',
        'description': sDescription,
        'keywords': 'guest details, wedding, seating planner, csv files',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }
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
    return render_template('guestdetails.html', meta=objMeta,
                           title=sPageTitle)


@catalog.route('/step3')
@catalog.route('/step3/<int:page>')
def step3(page=1):
    sPageTitle = 'Guest Review - MyWeddingSeatingPlanner.com'
    sDescription = 'Provide further details about your guests to the system. This is needed to ensure that the seating plan is correct.'
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
    objMeta = {
        'googlebot': 'index,follow,snippet,archive',
        'description': sDescription,
        'keywords': 'guests, wedding, seating plan',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }

    return render_template('guestreview.html', meta=objMeta,
                           title=sPageTitle, guests=guestconfig)


@catalog.route('/demo')
def demo():
    sPageTitle = 'Sample results of the application - MyWeddingSeatingPlanner.com'
    sDescription = 'A sample results generated by the application. The guests and their relationships were randomly generated.'
    objMeta = {
        'googlebot': 'index,follow,snippet,archive',
        'description': sDescription,
        'keywords': 'Demo, seating plan, wedding',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }
    '''
    numguest = 75  # 100
    numtable = 15
    min_known_neighbors = 1
    table_capacity = 5  # 7 too is a good number
    start_time = time.time()
    G = nx.random_regular_graph(4, numguest)  # 5 is a good number
    e = [(u, v, {'weight': 50}) for u, nbrs in G.adj.items() for v in nbrs]
    f = [(u, u) for u in G.nodes()]
    update = e + f
    G.update(edges=update)
    C = nx.adjacency_matrix(G).todense().tolist()
    guestlist = [Guest(i + 1, "Guest " + str(i + 1)) for i in range(numguest)]
    names = [i['name'] for i in guestlist]
    solution = WeddingChartPrinter.solve_with_discrete_model(numtable, table_capacity, min_known_neighbors, C, names)
    print('solution: ', solution)
    current_time = time.time()
    '''

    numguests = 105
    guestpertable = 7
    numtables = 15
    guestlist = ["Guest " + str(i + 1) for i in range(numguests)]
    random.shuffle(guestlist)
    solution = {}
    for i in range(numtables):
        solution['Table %d' % (i + 1)] = guestlist[i * guestpertable:i * guestpertable + guestpertable]

    return render_template('demo.html', meta=objMeta,
                           title=sPageTitle, seating=solution)


@catalog.route('/results')
def results():
    sPageTitle = 'Results page - MyWeddingSeatingPlanner.com'
    sDescription = 'Your seating plan for your wedding as generated by us.'
    objMeta = {
        'googlebot': 'index,follow,snippet,archive',
        'description': sDescription,
        'keywords': 'seating plans, wedding, guests, seats',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }
    # numguests = int(session['config']['numguest'])
    num_tables = int(session['config']['numtables'])
    table_capacity = int(session['config']['numguestspertable'])
    min_known_neighbors = 1
    # min_known_neighbors = int(session['config']['minguestpertable'])
    names = [i['name'] for i in session['guestlist']]

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

    # stripe payment data
    stripejs, stripeobj = StripeWrapper.generatePaymentData(session['user_id'], stripekey, request.url_root)
    sol = dict(list(solution.items())[:len(solution)//2])
    return render_template('results.html', meta=objMeta,
                           title=sPageTitle, seating=sol, extrajs=stripejs, stripeobj=stripeobj)


@catalog.route('/cancel/<sessionid>')
def rendercancellationpage(sessionid):
    sPageTitle = 'Payment Cancellation page - MyWeddingSeatingPlanner.com'
    sDescription = 'Your seating plan for your wedding as generated by us.'
    objMeta = {
        'googlebot': 'index,follow,snippet,archive',
        'description': sDescription,
        'keywords': 'seating plans, wedding, guests, seats, payment failure',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }
    seatingplan = SeatingPlan.query.filter_by(sessionid=sessionid).first_or_404()
    if seatingplan:
        d1 = seatingplan.solutiondate
        t = datetime.today()
        delta = t - d1
        #print('[INFO] num days = ', delta.days)

    # stripe payment data
    stripejs, stripeobj = StripeWrapper.generatePaymentData(sessionid, stripekey, request.url_root)
    sol = seatingplan.solution
    return render_template('cancel.html', seating=dict(list(sol.items())[:len(sol)//2]),
                           title=sPageTitle,
                           extrajs=stripejs, stripeobj=stripeobj, meta=objMeta
                           )


@catalog.route('/paymentsuccess/<sessionid>', methods=['POST', 'GET'])
def rendersuccesspage(sessionid):
    result = StripeWrapper.verifypayment(stripekey, request)
    seatingplan = SeatingPlan.query.filter_by(sessionid=sessionid).first_or_404()
    sPageTitle = 'Payment Success page - MyWeddingSeatingPlanner.com'
    sDescription = 'Your seating plan for your wedding as generated by us.'
    objMeta = {
        'googlebot': 'index,follow,snippet,archive',
        'description': sDescription,
        'keywords': 'thank you, payment page, success, seats, wedding',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }

    if result:
        return render_template('paymentsuccess.html', meta=objMeta,
                               sessionid=sessionid, title=sPageTitle)
    else:
        # render cancel page with an error message
        return render_template('cancel.html', meta=objMeta,
                               seating=seatingplan.solution,
                               title=sPageTitle)


@catalog.route('/seating_<sessionid>.pdf')
def seatingpdf(sessionid):
    seatingplan = SeatingPlan.query.filter_by(sessionid=sessionid).first_or_404()
    html = render_template('seatingpdf.html', seating=seatingplan.solution)
    return render_pdf(HTML(string=html))


@catalog.route('/guest', methods=['POST'])
@catalog.route('/guest/<int:guestid>', methods=['GET', 'POST'])
def editguest(guestid=None):
    response = {}
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
    sPageTitle = 'seating plans - MyWeddingSeatingPlanner.com'
    sDescription = 'Your seating plan for your wedding as generated by us.'
    objMeta = {
        'googlebot': 'noindex,nofollow,snippet,archive',
        'description': 'admin page for seating plans',
        'keywords': 'seating plans',
        'publisher': 'BahamSoft Ltd',
        'og:title': sPageTitle,
        'og:description': sDescription
    }
    res = SeatingPlan.query.order_by(desc(SeatingPlan.solutiondate)).paginate(page, 10)
    num = len(SeatingPlan.query.all())
    return render_template('seatingplans.html', meta=objMeta,
                           seatingplans=res, title=sPageTitle, total=num)
