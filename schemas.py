"""
Database Schemas for BookMyShow-style app

Each Pydantic model corresponds to a MongoDB collection. The collection name is the
lowercase of the class name (e.g., Movie -> "movie").
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class Movie(BaseModel):
    title: str = Field(..., description="Movie title")
    poster_url: Optional[str] = Field(None, description="Poster image URL")
    languages: List[str] = Field(default_factory=list, description="Available languages")
    genres: List[str] = Field(default_factory=list, description="Genres")
    rating: Optional[float] = Field(None, ge=0, le=10, description="Rating out of 10")
    runtime_mins: Optional[int] = Field(None, description="Runtime in minutes")
    certification: Optional[str] = Field(None, description="Certification e.g. UA, U, A")
    synopsis: Optional[str] = Field(None, description="Short description")

class Cinema(BaseModel):
    name: str = Field(..., description="Cinema name")
    city: str = Field(..., description="City name")
    address: Optional[str] = Field(None, description="Street address")

class Screen(BaseModel):
    cinema_id: str = Field(..., description="Reference to cinema _id as string")
    name: str = Field(..., description="Screen name e.g., Screen 1")
    rows: int = Field(..., ge=1, le=20, description="Number of seat rows")
    seats_per_row: int = Field(..., ge=1, le=30, description="Seats per row")

class Showtime(BaseModel):
    movie_id: str = Field(..., description="Reference to movie _id as string")
    cinema_id: str = Field(..., description="Reference to cinema _id as string")
    screen_id: str = Field(..., description="Reference to screen _id as string")
    start_time: str = Field(..., description="ISO datetime string for show start")
    language: str = Field(..., description="Language of the show")
    price_map: dict = Field(default_factory=dict, description="Seat category to price mapping")

class Booking(BaseModel):
    showtime_id: str = Field(..., description="Reference to showtime _id as string")
    customer_name: str = Field(..., description="Name of customer")
    customer_email: str = Field(..., description="Email of customer")
    seats: List[str] = Field(..., description="List of seat codes e.g., A1, A2")
    total_amount: float = Field(..., ge=0, description="Total booking amount")
