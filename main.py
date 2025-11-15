import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta

from database import db, create_document, get_documents
from schemas import Movie, Cinema, Screen, Showtime, Booking

app = FastAPI(title="ShowTime API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def to_str_id(doc):
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"]) if "_id" in doc else None
    return doc

# Seed data route for demo
class SeedResponse(BaseModel):
    movies: int
    cinemas: int
    screens: int
    showtimes: int

@app.post("/seed", response_model=SeedResponse)
def seed():
    """Seed a minimal dataset for demo usage."""
    # Avoid duplicate seed: if movies exist, skip
    if db["movie"].count_documents({}) > 0:
        return SeedResponse(
            movies=db["movie"].count_documents({}),
            cinemas=db["cinema"].count_documents({}),
            screens=db["screen"].count_documents({}),
            showtimes=db["showtime"].count_documents({}),
        )

    # Movies
    m1 = Movie(
        title="The Red Horizon",
        poster_url="https://images.unsplash.com/photo-1517602302552-471fe67acf66?w=800",
        languages=["English", "Hindi"],
        genres=["Action", "Adventure"],
        rating=8.1,
        runtime_mins=132,
        certification="UA",
        synopsis="A daring mission to save the world from a looming threat.",
    )
    m2 = Movie(
        title="City Serenade",
        poster_url="https://images.unsplash.com/photo-1517604931442-7e0c8ed2963f?w=800",
        languages=["English"],
        genres=["Drama", "Romance"],
        rating=7.4,
        runtime_mins=115,
        certification="U",
        synopsis="Two strangers connect through music and chance encounters.",
    )

    m1_id = create_document("movie", m1)
    m2_id = create_document("movie", m2)

    # Cinemas
    c1_id = create_document("cinema", {"name": "Downtown Multiplex", "city": "Mumbai", "address": "MG Road"})
    c2_id = create_document("cinema", {"name": "Skyline Cinemas", "city": "Mumbai", "address": "Bandra West"})

    # Screens
    s1_id = create_document("screen", {"cinema_id": c1_id, "name": "Screen 1", "rows": 8, "seats_per_row": 12})
    s2_id = create_document("screen", {"cinema_id": c1_id, "name": "Screen 2", "rows": 10, "seats_per_row": 12})
    s3_id = create_document("screen", {"cinema_id": c2_id, "name": "Prime Screen", "rows": 9, "seats_per_row": 14})

    # Showtimes for next 3 days
    base = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    times = [base + timedelta(hours=h) for h in [12, 15, 18, 21]]
    price_map = {"Silver": 200.0, "Gold": 350.0, "Platinum": 500.0}

    for show_day in range(3):
        day = base + timedelta(days=show_day)
        for t in times:
            start = datetime(day.year, day.month, day.day, t.hour, 0, 0).isoformat()
            create_document("showtime", {
                "movie_id": m1_id,
                "cinema_id": c1_id,
                "screen_id": s1_id,
                "start_time": start,
                "language": "English",
                "price_map": price_map
            })
            create_document("showtime", {
                "movie_id": m2_id,
                "cinema_id": c2_id,
                "screen_id": s3_id,
                "start_time": start,
                "language": "English",
                "price_map": price_map
            })

    return SeedResponse(
        movies=db["movie"].count_documents({}),
        cinemas=db["cinema"].count_documents({}),
        screens=db["screen"].count_documents({}),
        showtimes=db["showtime"].count_documents({}),
    )

@app.get("/")
def root():
    return {"message": "ShowTime API running"}

@app.get("/movies")
def list_movies():
    docs = get_documents("movie")
    return [to_str_id(d) for d in docs]

@app.get("/movies/{movie_id}")
def get_movie(movie_id: str):
    doc = db["movie"].find_one({"_id": ObjectId(movie_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Movie not found")
    return to_str_id(doc)

@app.get("/cinemas")
def list_cinemas(city: Optional[str] = None):
    q = {"city": city} if city else {}
    docs = get_documents("cinema", q)
    return [to_str_id(d) for d in docs]

@app.get("/showtimes")
def list_showtimes(movie_id: Optional[str] = None, city: Optional[str] = None, date: Optional[str] = None):
    q = {}
    if movie_id:
        q["movie_id"] = movie_id
    if city:
        cinema_ids = [str(c["_id"]) for c in db["cinema"].find({"city": city}, {"_id": 1})]
        q["cinema_id"] = {"$in": cinema_ids} if cinema_ids else "__none__"
    if date:
        # Filter by date prefix of ISO string
        q["start_time"] = {"$regex": f"^{date}"}
    docs = get_documents("showtime", q)
    # Attach movie and cinema names
    for d in docs:
        try:
            movie = db["movie"].find_one({"_id": ObjectId(d["movie_id"])}, {"title": 1})
            cinema = db["cinema"].find_one({"_id": ObjectId(d["cinema_id"])}, {"name": 1})
            d["movie_title"] = movie.get("title") if movie else None
            d["cinema_name"] = cinema.get("name") if cinema else None
        except Exception:
            pass
    return [to_str_id(d) for d in docs]

@app.get("/seats/{showtime_id}")
def get_seats(showtime_id: str):
    st = db["showtime"].find_one({"_id": ObjectId(showtime_id)})
    if not st:
        raise HTTPException(status_code=404, detail="Showtime not found")
    screen = db["screen"].find_one({"_id": ObjectId(st["screen_id"])})
    rows = screen.get("rows", 8)
    seats_per_row = screen.get("seats_per_row", 12)

    # Booked seats
    booked_docs = db["booking"].find({"showtime_id": showtime_id}, {"seats": 1})
    booked = set()
    for b in booked_docs:
        for s in b.get("seats", []):
            booked.add(s)

    grid = []
    for r in range(rows):
        row_label = chr(ord('A') + r)
        row = []
        for c in range(1, seats_per_row + 1):
            code = f"{row_label}{c}"
            row.append({"code": code, "available": code not in booked})
        grid.append(row)

    return {"grid": grid, "price_map": st.get("price_map", {})}

class BookingRequest(BaseModel):
    showtime_id: str
    customer_name: str
    customer_email: str
    seats: List[str]

@app.post("/book")
def book_seats(req: BookingRequest):
    # Validate showtime
    st = db["showtime"].find_one({"_id": ObjectId(req.showtime_id)})
    if not st:
        raise HTTPException(status_code=404, detail="Showtime not found")

    # Check availability atomically-ish
    existing = list(db["booking"].find({"showtime_id": req.showtime_id, "seats": {"$in": req.seats}}))
    if existing:
        raise HTTPException(status_code=409, detail="Some seats are already booked")

    # Calculate total using base price (Platinum if closer to center else Gold/Silver)
    base_price = st.get("price_map", {}).get("Gold", 300.0)
    total = base_price * len(req.seats)

    booking = Booking(
        showtime_id=req.showtime_id,
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        seats=req.seats,
        total_amount=float(total)
    )
    booking_id = create_document("booking", booking)
    return {"booking_id": booking_id, "total": total}

@app.get("/test")
def test_database():
    from database import db as _db
    try:
        collections = _db.list_collection_names()
        return {"backend": "running", "database": "connected", "collections": collections}
    except Exception as e:
        return {"backend": "running", "database": f"error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
