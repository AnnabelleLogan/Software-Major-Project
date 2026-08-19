from flask import Flask, request, render_template, redirect, url_for
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///Users.db")

app = Flask(__name__)

engine = create_engine('sqlite:///.database/Users.db')