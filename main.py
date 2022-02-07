from re import L
import re
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask.wrappers import Request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
from sqlalchemy.orm import query
import sqlite3 
import json,uuid,os,sqlite3
from flask import jsonify
import io
from applications.validation import No_cards_error,Invalid_error
from werkzeug.exceptions import HTTPException
from sqlalchemy.orm import session
import time 
from datetime import datetime 


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flashcard.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class deck_info(db.Model):
    Deck_id = db.Column(db.Integer, primary_key = True, nullable = False)
    Deck_name = db.Column(db.Text, nullable = False)
    Deck_location = db.Column(db.Text, nullable = False)
    db.UniqueConstraint(Deck_id,Deck_name)

class Credentials(db.Model):
    User_id = db.Column(db.Integer, primary_key = True, autoincrement = True, nullable = False)
    Username = db.Column(db.Text, nullable = False)
    Password = db.Column(db.Text,nullable = False)
    db.UniqueConstraint(User_id,Username)

class Dashboard_info(db.Model):
    id = db.Column(db.Integer, primary_key = True, autoincrement = True,nullable = False)
    User_id = db.Column(db.Integer, db.ForeignKey(Credentials.User_id),nullable = False)
    Deck_id = db.Column(db.Text, db.ForeignKey('deck_info.Deck_id'), nullable = False)
    Score = db.Column(db.Integer)
    LastReviewTime = db.Column(db.Text)

@app.route('/dashboard/<int:User_id>')
def dashboard(User_id):
    User_id = int(User_id)
    dash = Dashboard_info.query.all()
    Decks = {}
    creds = Credentials.query.get(User_id)
    name = creds.Username
    for d in dash:
        decks = deck_info.query.get(d.Deck_id)
        Decks[d.Deck_id] = decks.Deck_name
    return render_template('dashboard.html', dashboard = dash, User_id = User_id,Username = name, decks=Decks)

@app.route('/login', methods = ['GET','POST'])
def login():
    if(request.method == 'GET'):
        return render_template('login.html')
    else:
        uname = request.form['username']
        password = request.form['password']
        
        user = db.session.query(Credentials).filter(Credentials.Username == uname).first()
        if user:
            if(user.Password == password):
                s = '/dashboard/' + str(user.User_id)
                return redirect(s)
            else:
                return redirect('/login/invalid')
        return render_template('invalid.html', argument = 'user')

@app.route('/login/invalid')
def InvalidLogin():
  return render_template('invalid.html', argument = 'login')

@app.route('/invalid/<int:User_id>/<string:argument>/')
def Invalid(User_id,argument):
    return render_template('invalid.html', argument = argument)


@app.route('/signup', methods = ['GET','POST'])
def signup():
    if(request.method == 'GET'):
        return render_template('signup.html')
    else:
        uname = request.form['username']
        password = request.form['password']
        creds = Credentials(Username = uname, Password = password)
        db.session.add(creds)
        db.session.commit()

        return redirect(url_for('login'))

@app.route('/update/<int:User_id>/<string:deck_id>',methods=['PUT'])
def Update(deck_id,User_id):
    if(request.method== 'PUT'):
        data=request.json
        try:
            Dashboard_info.query.filter(Dashboard_info.Deck_id==deck_id ,Dashboard_info.User_id==User_id).one()
        except exc.SQLAlchemyError:
            raise Invalid_error("USER ID", status_code=400)
        if data:
           
            try:
                deck_records= deck_info.query.filter(deck_info.Deck_id==deck_id).one()
           
                location=deck_records.Deck_location
           
                deck_name=deck_records.Deck_name
           
            except exc.SQLAlchemyError:
                raise Invalid_error('Deck_id',status_code=400)
            data_json = io.open(location,'r',encoding='UTF-8').read()
            data_dic=json.loads(data_json)
            for keys in data:
                data_dic["cards"][keys]= data[keys]
            with open(location, "w") as outfile:
                json.dump(data_dic, outfile, indent = 4)
            return data_dic
        else: 
            raise No_cards_error(status_code=404)


@app.route('/update/<int:User_id>', methods = ['GET','POST'])
def Update_deck(User_id):
    if(request.method == 'GET'):
        try:
            Credentials.query.filter(Credentials.User_id==User_id).one()
        except exc.SQLAlchemyError:
            return render_template("Invalid_deck.html",User_id=User_id,data= "USER ID/DECK ID")
        creds = Credentials.query.get(User_id)
        name = creds.Username        
        return render_template('updatedeck1.html',Username = name)
    else:
        deckId = request.form['deckId']
        cardNo  = request.form['cardno']
        url = '/updatedeck/'+'/'+str(User_id)+'/' + deckId + '/' + str(cardNo)
        return redirect(url)

@app.route('/updatedeck/<string:User_id>/<string:deckId>/<int:cardNo>', methods = ['GET','POST'])    
def Update_card(deckId,cardNo,User_id):
    if(request.method == 'GET'):
        try:
            Dashboard_info.query.filter(Dashboard_info.Deck_id==deckId ,Dashboard_info.User_id==User_id).one()
        except exc.SQLAlchemyError:
            return render_template('Invalid_deck.html',User_id=User_id, data = "USER ID/DECK ID")
        try:
            deck_records= deck_info.query.filter(deck_info.Deck_id==deckId).one()
        except exc.SQLAlchemyError:
                return render_template('Invalid_deck.html',User_id=User_id, data = "DECK ID")
        deckName=deck_records.Deck_name
        creds = Credentials.query.get(User_id)
        name = creds.Username
        return render_template('updatedeck2.html',cardNo=cardNo,deckName=deckName,Username = name)
    else:
        r = request.form
        r = str(r)
        r = r[20:-2]
        data = str2tupleList(r, cardNo)
        if data=={'':''}:
            return render_template('NoCards.html',User_id=User_id)
        deck_records= deck_info.query.filter(deck_info.Deck_id==deckId).one_or_none()
        if deck_records is not None:
            location=deck_records.Deck_location
            deckName=deck_records.Deck_name
            data_json = io.open(location,'r',encoding='UTF-8').read()
            data_dic=json.loads(data_json)
            for keys in data:
                data_dic["cards"][keys]= data[keys]
            with open(location, "w") as outfile:
                json.dump(data_dic, outfile, indent = 4)
            creds = Credentials.query.get(User_id)
            name = creds.Username    
            return render_template('showDeck.html',Username=name,deckName=deckName,deckId=deckId,cards=data_dic['cards'],User_id=User_id)
        else :
            return render_template('Invalid_deck.html',User_id=User_id, data = "DECK ID")

@app.route('/delete/<int:User_id>/<string:deck_id>',methods=['PUT'])
def Delete(deck_id,User_id):    
    if(request.method=='PUT'):
        try:
            Dashboard_info.query.filter(Dashboard_info.Deck_id==deck_id ,Dashboard_info.User_id==User_id).one()
        except exc.SQLAlchemyError:
            raise Invalid_error('USER ID/DECK ID,this deck for this user', status_code=400)
        deck_records= deck_info.query.filter(deck_info.Deck_id==deck_id).one()
        location=deck_records.Deck_location
        os.remove(location)
        deck=deck_info.query.filter(deck_info.Deck_id==deck_id).delete()
        db.session.commit()
        dash=Dashboard_info.query.filter(Dashboard_info.Deck_id==deck_id).delete()
        db.session.commit()
        return jsonify("Deck Removed")

@app.route('/delete/<int:User_id>',methods=['POST','GET'])
def Delete_deck(User_id):
    if(request.method=='GET'):
        try:
            Credentials.query.filter(Credentials.User_id==User_id).one()
        except exc.SQLAlchemyError:
            return render_template("Invalid_deck.html",User_id=User_id,data= "USER ID")
        creds = Credentials.query.get(User_id)
        name = creds.Username    
        return render_template('deleteDeck1.html',Username=name)
    else:
        deckId = request.form['deckId']   
        try:
            deck_records= deck_info.query.filter(deck_info.Deck_id==deckId).one()
        except exc.SQLAlchemyError:
            return render_template('Invalid_deck.html',User_id=User_id, data = "DECK ID")
        location=deck_records.Deck_location
        os.remove(location)
        deck_info.query.filter(deck_info.Deck_id==deckId).delete()
        db.session.commit()
        Dashboard_info.query.filter(Dashboard_info.Deck_id==deckId).delete()
        db.session.commit()
        creds = Credentials.query.get(User_id)
        name = creds.Username
        return render_template('deleteDeck2.html',User_id=User_id,Username=name)

@app.route('/remove/<int:User_id>/<string:deck_id>/<string:card_name>',methods=['PUT'])
def Remove_card_info(deck_id,card_name,User_id):
    if(request.method== 'PUT'):
        try:
            Dashboard_info.query.filter(Dashboard_info.Deck_id==deck_id ,Dashboard_info.User_id==User_id).one()
        except exc.SQLAlchemyError:
            raise Invalid_error("USER ID/DECK ID,this deck for this user", status_code=400)
        # try:
        #     deck_records= deck_info.query.filter(deck_info.Deck_id==deck_id).one()
        # except exc.SQLAlchemyError:
        #     raise Invalid_error('Deck_id')
        deck_records= deck_info.query.filter(deck_info.Deck_id==deck_id).one()    
        location=deck_records.Deck_location
        deck_name=deck_records.Deck_name
        data_json = io.open(location,'r',encoding='UTF-8').read()
        data_dic=json.loads(data_json)
        try:
            del data_dic["cards"][card_name]
        except KeyError:
            raise Invalid_error('card_name',status_code=404)    
        with open(location, "w") as outfile:
            json.dump(data_dic, outfile, indent = 4)
        return data_dic 


@app.route('/remove/<int:User_id>',methods=['GET','POST'])
def remove_card(User_id):
    if(request.method == 'GET'):
        try:
            Credentials.query.filter(Credentials.User_id==User_id).one()
        except exc.SQLAlchemyError:
            return render_template("Invalid_deck.html",User_id=User_id,data= "USER ID")
        creds = Credentials.query.get(User_id)
        name = creds.Username    
        return render_template('remove1.html',Username = name)
    elif(request.method =='POST'):
        deckId = request.form['deckId']
        url = '/remove/'+str(User_id)+'/'+deckId
        return redirect(url)

@app.route('/remove/<int:User_id>/<string:deckId>',methods=['GET','POST'])
def remove_card2(User_id,deckId):
    if(request.method=='GET'):
        try:
            Dashboard_info.query.filter(Dashboard_info.Deck_id==deckId ,Dashboard_info.User_id==User_id).one()
        except exc.SQLAlchemyError:
            return render_template('Invalid_deck.html',User_id=User_id, data = "USER ID/DECK ID")
        deck_records= deck_info.query.filter(deck_info.Deck_id==deckId).one()   
        location=deck_records.Deck_location
        deckName=deck_records.Deck_name
        data_json = io.open(location,'r',encoding='UTF-8').read()
        data_dic=json.loads(data_json)
        data_dic=dict(data_dic)
        creds = Credentials.query.get(User_id)
        name = creds.Username
        return render_template('remove2.html',cards=data_dic['cards'],Username =name)
    elif(request.method=='POST'):
        cardName = request.form['front']
        try:
            deck_records= deck_info.query.filter(deck_info.Deck_id==deckId).one()
        except exc.SQLAlchemyError:
            return render_template('Invalid_deck.html',User_id=User_id, data = "DECK ID")
        location=deck_records.Deck_location
        deckName=deck_records.Deck_name
        data_json = io.open(location,'r',encoding='UTF-8').read()
        data_dic=json.loads(data_json)
        try:
            del data_dic["cards"][cardName]
        except KeyError:
            User_id = User_id
            return render_template('No_such_card.html',User_id=User_id) 
        with open(location, "w") as outfile:
            json.dump(data_dic, outfile, indent = 4)
        creds = Credentials.query.get(User_id)
        name = creds.Username    
        return render_template('showDeck.html',deckName=deckName,Username=name,deckId=deckId,cards=data_dic['cards'],User_id=User_id)    

        
@app.route('/new/<int:User_id>/<string:deck_name>',methods=['POST'])
def New_deck(deck_name,User_id):
    if(request.method == 'POST'):
        data=request.json
        try:
            Credentials.query.filter(Credentials.User_id==User_id).one()
        except exc.SQLAlchemyError:
            raise Invalid_error("USER ID",status_code=400)
        if data :
            deckId = str(uuid.uuid4())[:8]
            dic = {"Deck_name":deck_name, "Deck_id":deckId,"cards":data}
            MyJson = json.dumps(dic, indent = 4)
            deck_location = str(os.path.join(basedir, "json/"+deck_name+".json"))
            F =open(deck_location, 'w')
            with open( deck_location, "w") as outfile:
                outfile.write(MyJson)  
            cards = deck_info(Deck_id=deckId,Deck_name=deck_name,Deck_location=deck_location)
            db.session.add(cards)
            db.session.commit()
            dash = Dashboard_info(Deck_id = deckId, User_id = User_id, Score = 0, LastReviewTime = '0')
            db.session.add(dash)
            db.session.commit()
            return jsonify(dic)
        else :
            raise No_cards_error(status_code=400)


@app.route('/new/<int:User_id>', methods = ['GET','POST'])
def new_deckfunc(User_id):
    if(request.method == 'GET'):
        try:
            Credentials.query.filter(Credentials.User_id==User_id).one()
        except exc.SQLAlchemyError:
            return render_template("Invalid_deck.html",User_id=User_id,data= "USER ID")
        creds = Credentials.query.get(User_id)
        name = creds.Username
        return render_template('createdeck1.html',Username = name)
    else:      
        deckName = request.form['deckname']
        cardNo  = request.form['cardno']
        url = '/setdeck/' + str(User_id) + '/' + deckName + '/' + str(cardNo)
        return redirect(url)
              
@app.route('/setdeck/<int:User_id>/<string:deckName>/<int:cardNo>', methods = ['GET','POST'])
def create(deckName, cardNo,User_id):
    if(request.method == 'GET'):
        try:
            Credentials.query.filter(Credentials.User_id==User_id).one()
        except exc.SQLAlchemyError:
            return render_template("Invalid_deck.html",User_id=User_id,data= "USER ID")
        creds = Credentials.query.get(User_id)
        name = creds.Username    
        return render_template('createdeck2.html',Username=name,cardno = cardNo, deckname = deckName)
    else:
        r = request.form
        r = str(r)
        r = r[20:-2]
        data = str2tupleList(r, cardNo)
        if data!= { '': ''}:
            deckId = str(uuid.uuid4())[:8]
            dic = {"Deck_name":deckName, "Deck_id":deckId,"cards":data}
            MyJson = json.dumps(dic, indent = 4)
            deckLocation = str(os.path.join(basedir, "json/"+deckName+".json"))
            F =open(deckLocation, 'w')
            with open( deckLocation, "w") as outfile:
                outfile.write(MyJson)  
            cards = deck_info(Deck_id=deckId,Deck_name=deckName,Deck_location=deckLocation)
            db.session.add(cards)
            db.session.commit()
            dash = Dashboard_info(Deck_id = deckId, User_id = User_id, Score = 0, LastReviewTime = '0')
            db.session.add(dash)
            db.session.commit()
            creds = Credentials.query.get(User_id)
            name = creds.Username
            return render_template('showDeck.html',deckName=deckName,deckId=deckId,cards=dic["cards"],User_id=User_id,Username=name)
        else : 
            return render_template('NoCards.html',User_id=User_id)

def str2tupleList(s, cardNo):
    r = eval( "[%s]" % s )
    dic = {}
    for i in range(0,cardNo):
        dic[r[i][1]] = r[i+cardNo][1]
    return dic 

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard/<int:User_id>/<string:Deck_id>/<int:card>/<int:score>')
def card_detail(User_id,card, Deck_id,score):
    Deck_details = deck_info.query.filter(deck_info.Deck_id == Deck_id).one()
    Deck_Name = Deck_details.Deck_name
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    Filename= Deck_Name +'.json'
    json_url = os.path.join(SITE_ROOT, "json/", Filename)
    data = json.load(open(json_url))
    li = list(data['cards'].keys())

    if(card!=0):
        dash= Dashboard_info.query.filter((Dashboard_info.User_id == User_id) & (Dashboard_info.Deck_id == Deck_id)).one()
        dash.Score += int(score)
        now = datetime.now()
        now = now.strftime("%d/%m/%Y %H:%M:%S")
        dash.LastReviewTime = now
        db.session.commit()

       
    if(card == len(li)):
        url = '/dashboard/' + str(User_id)   
        return redirect(url)
    
    else:
        front = li[card]
        back = data['cards'][front]

        return render_template('review.html', User_id = User_id, Deck_id = Deck_id, Deck_Name = Deck_Name, card = card+1, front = front, back = back)

@app.route('/about')
def about():
    return render_template('about.html')
    
@app.route('/api.yaml')
def document():
    return render_template('/api.yaml')  

@app.route('/getuserid/<string:Username>/<string:password>')
def getuserid(Username, password):
    
        cred = Credentials.query.filter(Credentials.Username == Username, Credentials.Password == password).one_or_none()

        if(cred):
            p = cred.User_id
            dic  = {}
            dic['User_id'] = p
    
            return jsonify(dic)

        else:
            raise Invalid_error('Username/password', status_code = 400)

if __name__ == "__main__":
    app.run(debug = True, host ='0.0.0.0')