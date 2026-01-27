Tourism Management Platform

A full-stack web application designed for tourism companies to manage tours, bookings, customers, and operational data. The system is built with Django as the backend framework, PostgreSQL as the primary database, and is deployed on AWS EC2 for scalability and reliability.

Tech Stack

Backend: Django (Python)

Database: PostgreSQL

Deployment: AWS EC2

Web Server: Gunicorn + Nginx (production)

OS: Linux (Ubuntu)

Features

Tour and destination management

Customer and booking records

Secure admin and staff access

REST-ready architecture for future frontend or mobile integration

Persistent data storage using PostgreSQL

Architecture Overview

Django handles business logic, authentication, and API endpoints

PostgreSQL stores structured tourism and booking data

EC2 hosts the application for flexible scaling and cloud deployment

Deployment Summary

Application runs on an EC2 instance

PostgreSQL configured as the production database

Environment variables used for secrets and credentials

Static files served via Nginx
