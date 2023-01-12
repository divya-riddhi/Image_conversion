import logging
import uuid
import psycopg2
from datetime import datetime, timedelta
import os
from typing import Tuple
from fastapi import FastAPI, Depends, HTTPException, File
from PIL import Image
from fastapi_jwt_auth import AuthJWT
from fastapi import Depends
import jwt

app = FastAPI()

secret_key = 'your secret key'
algorithm = 'HS256'

# configure log
logger = logging.getLogger("API_logger")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

file_handler = logging.FileHandler("api.log")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(file_handler)


@app.post("/login")
async def login(username: str, password: str):
    # check the username,password with the DB
    # in this example, check if the given username and password match a hardcoded value
    if username != "testuser" or password != "testpassword":
        logger.info("Incorrect username or password")
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    payload = {"sub": username}
    expires_delta = timedelta(minutes=15)
    expires = datetime.utcnow() + expires_delta
    access_token = jwt.encode(
        {"exp": expires, "iat": datetime.utcnow(), **payload},
        secret_key,
        algorithm=algorithm,
    ).decode("utf-8")

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/convert/jpeg-to-png")
async def convert_jpeg_to_png(token:str, image: bytes = File(...)):
    try:
        payload = AuthJWT.decode_token(token, secret_key=secret_key, algorithm=algorithm)
        # validate user and check if the user have access to the endpoint
    except AuthJWT.InvalidTokenError:
        logger.info("Invalid Token")
        raise HTTPException(status_code=400, detail="Invalid Token")
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    try:
        # Generate unique file names
        jpeg_file_name = f'{uuid.uuid4().hex}.jpg'
        png_file_name = f'{uuid.uuid4().hex}.png'

        # Save the image to the file system
        with open(f"images/{jpeg_file_name}", 'wb') as f:
            f.write(image)

        # Open the image and convert it to PNG
        with Image.open(f"images/{jpeg_file_name}") as image:
            image.save(f"images/{png_file_name}", "PNG")
       
        connection = psycopg2.connect(
            host="localhost",
            database="test_db",
            user="postgres",
            password="root"
        )
       
        cursor = connection.cursor()

        # Insert the request details into the database

        file_url = f"http://127.0.0.1:8000/images/{png_file_name}"
        tdate=datetime.now()
        status="success"
        
        # cursor.execute(f"INSERT INTO conversion_details (image_url, created_at) VALUES ('http://127.0.0.1:8000/images/{file_name}','{datetime.now()}')")
        cursor.execute("INSERT INTO convertion_req (source_file, image_url, created_at, status) VALUES (%s,%s, %s,%s)", (jpeg_file_name,file_url, tdate,"success"))
        connection.commit()
        
        # Close the cursor and connection
        cursor.close()
        connection.close()
        logger.info(f'{jpeg_file_name} converted to png and url is {file_url}')
        return {"png-url": file_url, "status": "success"}
    except Exception as e:
        logger.error(str(e))
        return {"status": "error", "message": str(e)}






@app.get("/list-conversion-requests")
async def list_conversion_requests():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="test_db",
            user="postgres",
            password="root"
        )

        cursor = connection.cursor()

        # Get all the records from the conversion_requests table
        cursor.execute("SELECT id, source_file, image_url, status, created_at FROM convertion_req")
        conversion_requests = cursor.fetchall()

        # Format the results
        result = []
        for request in conversion_requests:
            result.append({
                "id": request[0],
                "source_file": request[1],
                "png-url": request[2],
                "status": request[3],
                "created_at": request[4].strftime("%Y-%m-%d %H:%M:%S")
            })

        # Close the cursor and connection
        cursor.close()
        connection.close()
        logger.info('List all conversion requests')
        return result
    except Exception as e:
        logger.error(str(e))
        return {"status": "error", "message": str(e)}









