import aiosqlite

DB_PATH = "shopping.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shopping_sessions (
                session_id TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                fecha      TEXT NOT NULL,
                lista_raw  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shopping_items (
                item_id            TEXT PRIMARY KEY,
                session_id         TEXT NOT NULL,
                nombre             TEXT NOT NULL,
                seccion            TEXT NOT NULL,
                comprado           INTEGER DEFAULT 0,
                timestamp_comprado TEXT,
                FOREIGN KEY (session_id) REFERENCES shopping_sessions(session_id)
            )
        """)
        await db.commit()


async def create_session(session_id: str, user_id: int, fecha: str, lista_raw: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO shopping_sessions (session_id, user_id, fecha, lista_raw) VALUES (?, ?, ?, ?)",
            (session_id, user_id, fecha, lista_raw),
        )
        await db.commit()


async def create_items(items: list[dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO shopping_items (item_id, session_id, nombre, seccion) VALUES (?, ?, ?, ?)",
            [(i["item_id"], i["session_id"], i["nombre"], i["seccion"]) for i in items],
        )
        await db.commit()


async def mark_item_comprado(item_id: str, comprado: bool, timestamp: str | None = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE shopping_items SET comprado = ?, timestamp_comprado = ? WHERE item_id = ?",
            (1 if comprado else 0, timestamp, item_id),
        )
        await db.commit()
