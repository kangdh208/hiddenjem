from flask import Flask, render_template, request, jsonify
app = Flask(__name__)

import requests, sys, certifi, jwt, datetime, hashlib

from bs4 import BeautifulSoup
from bson.objectid import ObjectId
from pymongo import MongoClient

client = MongoClient('mongodb+srv://siwon:rlaznf11@cluster0.icysouv.mongodb.net/?retryWrites=true&w=majority')
db = client.dbsiwon

ca = certifi.where()

SECRET_KEY = "SPARTA"


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/store", methods=["POST"])
def store_post():
    url_receive = request.form['url_give']
    comment_receive = request.form['comment_give']
    star_receive = request.form['star_give']
    
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(url_receive, headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')

    store_name = soup.select_one('body > main > article > div.column-wrapper > div.column-contents > div > section.restaurant-detail > header > div.restaurant_title_wrap > span > h1').text
    category = soup.select_one('body > main > article > div.column-wrapper > div.column-contents > div > section.restaurant-detail > table > tbody > tr:nth-child(3) > td > span').text
    address = soup.select_one('body > main > article > div.column-wrapper > div.column-contents > div > section.restaurant-detail > table > tbody > tr:nth-child(1) > td').text.split('지번')
    img_url = soup.find("img")["src"]
    like = 0

    store = {
        "store_name": store_name,
        "address" : address[0],
        "category" : category,
        "image" : img_url,
        "store_comment": comment_receive,
        "star": star_receive,
        "like": like
    }

    db.stores.insert_one(store)
    return jsonify({"msg": "Store is Successfully Saved!"})


# Read
@app.route("/store", methods=["GET"])
def store_get():
    stores = list(db.stores.find())
    for store in stores:
        store['_id'] = str(store['_id'])

    return jsonify({"stores": stores})

# # Update

# # Delete
# @app.route("/store/<int:id>", methods=["DELETE"])
# def delete_store(id):
#     for i, store in enumerate(stores):
#         if store["id"] == id:
#             stores.pop(i)
#             return jsonify(stores)
#     return jsonify("삭제 불가능한 식당입니다")

# Like button
@app.route("/like", methods=["POST"])
def like_update():
    id_receive = request.form['id_give']
    print(id_receive)
    print(repr(ObjectId(id_receive)))
    like = db.stores.find_one({"_id": ObjectId(id_receive)}, {"like": 1})
    num_like = int(like["like"]) + 1
    print(num_like)
    before_like = { 'like': like["like"]}
    add_like = { '$set': {'like': num_like }}
    db.stores.update_one(before_like, add_like)
    return jsonify({'msg': 'like is increased by 1'})


#################################
##  HTML을 주는 부분             ##
#################################
# @app.route("/")
# def home():
#     token_receive = request.cookies.get("mytoken")
#     try:
#         payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
#         user_info = db.user.find_one({"id": payload["id"]})
#         return render_template("index.html", nickname=user_info["nick"])
#     except jwt.ExpiredSignatureError:
#         return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
#     except jwt.exceptions.DecodeError:
#         return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route("/login")
def login():
    msg = request.args.get("msg")
    return render_template("login.html", msg=msg)


@app.route("/register")
def register():
    return render_template("register.html")


#################################
##  로그인을 위한 API           ##
#################################

# [회원가입 API]
# id, pw, nickname을 받아서, mongoDB에 저장합니다.
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route("/api/register", methods=["POST"])
def api_register():
    id_receive = request.form["id_give"]
    pw_receive = request.form["pw_give"]
    nickname_receive = request.form["nickname_give"]

    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()

    db.user.insert_one({"id": id_receive, "pw": pw_hash, "nick": nickname_receive})

    return jsonify({"result": "success"})


# [로그인 API]
# id, pw를 받아서 맞춰보고, 토큰을 만들어 발급합니다.
@app.route("/api/login", methods=["POST"])
def api_login():
    id_receive = request.form["id_give"]
    pw_receive = request.form["pw_give"]

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.user.find_one({"id": id_receive, "pw": pw_hash})

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰에는, payload와 시크릿키가 필요합니다.
        # 시크릿키가 있어야 토큰을 디코딩(=풀기) 해서 payload 값을 볼 수 있습니다.
        # 아래에선 id와 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저ID 값을 알 수 있습니다.
        # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
        payload = {
            "id": id_receive,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=5),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        # token을 줍니다.
        return jsonify({"result": "success", "token": token})
    # 찾지 못하면
    else:
        return jsonify({"result": "fail", "msg": "아이디/비밀번호가 일치하지 않습니다."})


# [유저 정보 확인 API]
# 로그인된 유저만 call 할 수 있는 API입니다.
# 유효한 토큰을 줘야 올바른 결과를 얻어갈 수 있습니다.
# (그렇지 않으면 남의 장바구니라든가, 정보를 누구나 볼 수 있겠죠?)
@app.route("/api/nick", methods=["GET"])
def api_valid():
    token_receive = request.cookies.get("mytoken")

    # try / catch 문?
    # try 아래를 실행했다가, 에러가 있으면 except 구분으로 가란 얘기입니다.

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        print(payload)

        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        # 여기에선 그 예로 닉네임을 보내주겠습니다.
        userinfo = db.user.find_one({"id": payload["id"]}, {"_id": 0})
        return jsonify({"result": "success", "nickname": userinfo["nick"]})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})



if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
