import asyncio
import os
from dotenv import load_dotenv
import asyncpg
import networkx as nx

load_dotenv()

async def main():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "tgid")
    )
    
    lines = await conn.fetch("SELECT id, nodeid1, nodeid2 FROM linesobj WHERE nodeid1 IS NOT NULL AND nodeid2 IS NOT NULL LIMIT 10000")
    import networkx as nx
    G = nx.Graph()
    for row in lines:
        G.add_edge(row['nodeid1'], row['nodeid2'], id=row['id'])
    
    print(f"Graph nodes: {G.number_of_nodes()}, edges: {G.number_of_edges()}")
    
    if G.number_of_nodes() > 0:
        nodes_list = list(G.nodes())
        start = nodes_list[0]
        end = nodes_list[-1]
        try:
            path = nx.shortest_path(G, start, end)
            print(f"Path from {start} to {end}: {path[:10]}... (length {len(path)})")
        except nx.NetworkXNoPath:
            print(f"No path from {start} to {end}")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
