# openedx-graded-discussion-xblock
In site/admin/oauth2/client/ we create new client with URL=REDIRECT_URI=http://localhost and get KEY and SECRET.    
In [l|c]ms.env.json we point settings for XBLOCK:    
    "XBLOCK_SETTINGS": {    
        "client_id": "KEY",    
        "client_secret": "SECRET"    
    },     
