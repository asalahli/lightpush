# lightpush


A lightweight push notification server for websites.


## Overview

When working with most traditional web frameworks (e.g. Django), adding real-time features to websites presents a big challenge. Some developers solve this problem by installing an auxiliary server (e.g. Tornado, or node.js+socket.io) to handle real-time part of the website. For something as simple as sending push notifications to the client, this solution is an overkill.

`lightpush` solves this problem with a simpler approach. Just run `lightpush` server and make clients connect to it. Then you can send those clients notifications by making a simple `POST` request to `lightpush`.


## Installation

1. Download `lightpush.py` to the server machine.
2. run `python lightpush.py`

As simple as that.

This will start the server in its default settings. You can customize it by passing command line arguments when starting `lightpush`.

Argumonet     | Description
--------------|------------
--host        | A hostname to serve lightpush at
--port        | Port number
--secret-key  | A key to identify connecting remote servers (more on this later)


E.g.:

    python lightpush.py --port=8000


## Usage


Assuming the server is running in its default settings.


### Connecting from clients (i.e. Browsers)

    ws = new WebSocket('ws://127.0.0.1:8086');
    ws.onmessage = function(e) {
      var message = e.data;
      
      // do something with the message here
    }


### Sending a notification

Notifications are send by making a `POST` request to `lightpush`. There are two headers that must be set, for `lightpush` to accept the request:

1. `Authorization` must be set to the secret-key that the server was started with.
2. `Lightpush-Message`, a custom header, must be set to the message you want to send to clients.

E.g. (Python code):

    import requests
  
    headers = {
      "Authorization" : "29e03fe7-9e8f-42b2-a9ac-2c9519bdf0b1",
      "Lightpush-Message": "refresh"
    }
    
    response = requests.post("127.0.0.1:8086", headers=headers)
    assert response.status_code == 202
    

