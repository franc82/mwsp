from my_app import db
from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, \
    TextAreaField, SubmitField
from wtforms.validators import InputRequired, Email
from ortools.sat.python import cp_model
import datetime
from sqlalchemy_jsonfield import JSONField
import stripe


class StripeWrapper:
    @staticmethod
    def generatePaymentData(sessionid, apikey, domainname):
        #print('[INFO] Stripe key to generate button: ', apikey)
        additionaljs = ["https://js.stripe.com/v3/"]
        stripe.api_key = apikey
        product = stripe.Product.create(
            name='Wedding plan',
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
            success_url='%spaymentsuccess/%s' % (domainname, sessionid),
            cancel_url='%scancel/%s' % (domainname, sessionid),
        )

        return additionaljs, stripe_session

    @staticmethod
    def verifypayment(sapikey, requestpayload):
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = requestpayload.headers.get('stripe-signature')

        try:
            event = stripe.Webhook.construct_event(
                payload=requestpayload.data, sig_header=signature, secret=sapikey)
            data = event['data']
        except Exception as e:
            return e

        event_type = event['type']

        return event_type == 'checkout.session.completed'


class WeddingChartPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, seats, names, num_tables, num_guests, max_solutions):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0
        self.__seats = seats
        self.__names = names
        self.__num_tables = num_tables
        self.__num_guests = num_guests
        self.__solution_limit = max_solutions
        self.__solutiondict = {}

    def on_solution_callback(self):
        self.__solution_count += 1

        for t in range(1, self.__num_tables+1):
            self.__solutiondict["Table %d: " % t] = []
            for g in range(self.__num_guests):
                if self.Value(self.__seats[(t-1, g)]):
                    self.__solutiondict["Table %d: " % t].append(self.__names[g])

        if self.__solution_count >= self.__solution_limit:
            self.StopSearch()

    def num_solutions(self):
        return self.__solution_count

    def getSolution(self):
        return self.__solutiondict

    @staticmethod
    def solve_with_discrete_model(num_tables, table_capacity, min_known_neighbors, C, names):
        num_guests = len(C)
        all_tables = range(num_tables)
        all_guests = range(num_guests)
        maxSolutions = 1

        # Create the cp model.
        model = cp_model.CpModel()

        #
        # Decision variables
        #
        seats = {}
        for t in all_tables:
            for g in all_guests:
                seats[(t, g)] = model.NewBoolVar("guest %i seats on table %i" % (g,
                                                                                 t))

        colocated = {}
        for g1 in range(num_guests - 1):
            for g2 in range(g1 + 1, num_guests):
                colocated[(g1, g2)] = model.NewBoolVar(
                    "guest %i seats with guest %i" % (g1, g2))

        same_table = {}
        for g1 in range(num_guests - 1):
            for g2 in range(g1 + 1, num_guests):
                for t in all_tables:
                    same_table[(g1, g2, t)] = model.NewBoolVar(
                        "guest %i seats with guest %i on table %i" % (g1, g2, t))

        # Objective
        model.Maximize(
            sum(C[g1][g2] * colocated[g1, g2]
                for g1 in range(num_guests - 1) for g2 in range(g1 + 1, num_guests)
                if C[g1][g2] > 0))

        #
        # Constraints
        #

        # Everybody seats at one table.
        for g in all_guests:
            model.Add(sum(seats[(t, g)] for t in all_tables) == 1)

        # Tables have a max capacity.
        for t in all_tables:
            model.Add(sum(seats[(t, g)] for g in all_guests) <= table_capacity)

        # Link colocated with seats
        for g1 in range(num_guests - 1):
            for g2 in range(g1 + 1, num_guests):
                for t in all_tables:
                    # Link same_table and seats.
                    model.AddBoolOr([
                        seats[(t, g1)].Not(), seats[(t, g2)].Not(),
                        same_table[(g1, g2, t)]
                    ])
                    model.AddImplication(same_table[(g1, g2, t)], seats[(t, g1)])
                    model.AddImplication(same_table[(g1, g2, t)], seats[(t, g2)])

                # Link colocated and same_table.
                model.Add(
                    sum(same_table[(g1, g2, t)]
                        for t in all_tables) == colocated[(g1, g2)])

        # Min known neighbors rule.
        for t in all_tables:
            model.Add(
                sum(same_table[(g1, g2, t)]
                    for g1 in range(num_guests - 1)
                    for g2 in range(g1 + 1, num_guests) for t in all_tables
                    if C[g1][g2] > 0) >= min_known_neighbors)

        # Symmetry breaking. First guest seats on the first table.
        model.Add(seats[(0, 0)] == 1)

        ### Solve model
        solver = cp_model.CpSolver()
        solution_printer = WeddingChartPrinter(seats, names, num_tables, num_guests, maxSolutions)
        solver.SolveWithSolutionCallback(model, solution_printer)
        return solution_printer.getSolution()


class SettingsForm(FlaskForm):
    guests = IntegerField('Number of Guests', validators=[InputRequired()])
    tables = IntegerField('Number of Tables', validators=[InputRequired()])
    guestpertables = IntegerField('Number of Guests Per Table', validators=[InputRequired()])
    minguestchoices = [(0, 'Select From ...')] + [(value, value) for value in range(1,11)]
    minguest = SelectField('MinGuests', choices=minguestchoices, validators=[InputRequired()], coerce=int)


class ContactForm(FlaskForm):
    name = StringField("Full Name", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired()])
    message = TextAreaField("Message", validators=[InputRequired()])
    submit = SubmitField("Send")


# inherit from the dict object to make it JSON serializable
class Guest(dict):
    def __init__(self, guest_id, name):
        self.id = guest_id
        #print('creating object: ', guest_id)
        self.name = name
        relationships = []
        acq = ''
        self.acq = acq
        self.friends = relationships
        dict.__init__(self, id=guest_id, name=name, acq=acq, friends=relationships)

    ''''
    def __repr__(self):
        return '<Guest:%d Name:%s>' % (self.id, self.name)

    def getname(self):
        return self.name
    '''


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(50), index=True)
    messagedate = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    email = db.Column(db.String(50))
    ipaddress = db.Column(db.String(50))
    useragent = db.Column(db.String(250))
    message = db.Column(db.Text)

    def __init__(self, fullname, email, message, ipaddress, useragent):
        self.fullname = fullname
        self.email = email
        self.message = message
        self.ipaddress = ipaddress
        self.useragent = useragent


class SeatingPlan(db.Model):
    __tablename__ = 'seatingplan'
    id = db.Column(db.Integer, primary_key=True)
    sessionid = db.Column(db.String(50), index=True)
    solution = db.Column(JSONField(enforce_string=True))
    solutiondate = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    sessiondata = db.Column(JSONField(enforce_string=True))

    def __init__(self, sessionid, solution, session):
        self.sessionid = sessionid
        self.solution = solution
        sessiondata = {
            'user_id': session['user_id'],
            'user_agent': session['user_agent'],
            'ip': session['ip'],
            'config': session['config'],
            'guestlist': session['guestlist']
        }
        self.sessiondata = sessiondata

    def __repr__(self):
        return '<SeatingPlan:%d sid:%s>' % (self.id, self.sessionid)


'''
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    price = db.Column(db.Float)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship(
        'Category', backref=db.backref('products', lazy='dynamic')
    )

    def __init__(self, name, price, category):
        self.name = name
        self.price = price
        self.category = category

    def __repr__(self):
        return '<Product %d>' % self.id


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Category %d>' % self.id
'''