import streamlit as st
from neo4j import GraphDatabase
from pyvis.network import Network
import streamlit.components.v1 as components

st.set_page_config(page_title="NYT Bestsellers Graph", layout="wide")

# -----------------------------
# NEO4J CONNECTION SETTINGS
# -----------------------------
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"     # your password
NEO4J_DB = "booksnyt"


# Consistent colors by label
COLOR_MAP = {
    "Book": "#6A0DAD",      # purple
    "Author": "#1E88E5",    # blue
    "Publisher": "#FB8C00", # orange
    "ListWeek": "#D81B60",  # pink/red
    "Season": "#00897B",    # teal
}


@st.cache_resource
def get_driver():
    # FIX: Increase connection_timeout to 300 seconds (5 minutes) for large imports
    return GraphDatabase.driver(
        NEO4J_URI, 
        auth=(NEO4J_USER, NEO4J_PASSWORD),
        connection_timeout=300
    )

def get_overview():
    """Get node labels and relationship types for the legend."""
    driver = get_driver()
    with driver.session(database=NEO4J_DB) as session:
        node_res = session.run(
            """
            MATCH (n)
            RETURN labels(n)[0] AS label, count(*) AS count
            ORDER BY label
            """
        )
        rel_res = session.run(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS rel_type, count(*) AS count
            ORDER BY rel_type
            """
        )

        node_rows = [r.data() for r in node_res]
        rel_rows = [r.data() for r in rel_res]

    return node_rows, rel_rows


def fetch_graph(limit=200):
    """Fetch a subgraph of Books and their neighboring nodes."""
    driver = get_driver()
    cypher = """
    MATCH (b:Book)-[r]->(x)
    RETURN b, r, x
    LIMIT $limit
    """

    nodes = {}
    edges = []

    with driver.session(database=NEO4J_DB) as session:
        result = session.run(cypher, limit=limit)
        for record in result:
            b = record["b"]
            x = record["x"]
            r = record["r"]

            # ---- Book node ----
            if b.id not in nodes:
                nodes[b.id] = {
                    "id": b.id,
                    "label": b.get("title", "Book"),
                    "group": "Book",
                    "props": {
                        "Title": b.get("title"),
                        "Published date": b.get("published_date"),
                        "ISBN13": b.get("isbn13"),
                    },
                }

            # ---- Neighbor node ----
            x_labels = list(x.labels)
            x_group = x_labels[0] if x_labels else "Node"

            display_label = (
                x.get("name")
                or x.get("title")
                or x.get("list_name")
                or x_group
            )

            # For ListWeek, include the date in the visible label
            if x_group == "ListWeek":
                list_name = x.get("list_name", "")
                week = x.get("bestsellers_date", "")
                display_label = f"{list_name} ({week})"

            if x.id not in nodes:
                props = {}
                if x_group == "Author":
                    props["Author"] = x.get("name")
                elif x_group == "Publisher":
                    props["Publisher"] = x.get("name")
                elif x_group == "Season":
                    props["Season"] = x.get("name")
                elif x_group == "ListWeek":
                    props["List name"] = x.get("list_name")
                    props["Bestsellers date"] = x.get("bestsellers_date")

                nodes[x.id] = {
                    "id": x.id,
                    "label": display_label,
                    "group": x_group,
                    "props": props,
                }

            # ---- Relationship edge ----
            rel_type = type(r).__name__ if hasattr(r, "__class__") else "RELATED_TO"
            edges.append((b.id, x.id, rel_type))

    return list(nodes.values()), edges


def make_pyvis_graph(nodes, edges, height="650px", width="100%"):
    """Build the main interactive graph (real data)."""
    net = Network(height=height, width=width, bgcolor="white", font_color="black")
    net.barnes_hut()

    # Add nodes
    for n in nodes:
        group = n["group"]
        color = COLOR_MAP.get(group, "#333333")

        # Tooltip content
        title_lines = [f"<b>{group}</b>"]
        for k, v in n["props"].items():
            if v is not None:
                title_lines.append(f"{k}: {v}")
        title_html = "<br>".join(title_lines)

        net.add_node(
            n["id"],
            label=n["label"],
            title=title_html,
            color=color,
            # make labels more readable
            font={"size": 18, "strokeWidth": 2},
        )

    # Add edges (no label clutter, just tooltip)
    for src, dst, rel_type in edges:
        net.add_edge(src, dst, title=rel_type)

    # Cleaner layout for presentation (less “spaghetti”)
    net.set_options("""
    var options = {
      "nodes": {
        "shape": "dot",
        "size": 16
      },
      "physics": {
        "stabilization": true,
        "barnesHut": {
          "gravitationalConstant": -25000,
          "springLength": 160
        }
      },
      "edges": {
        "smooth": false
      }
    }
    """)
    return net


def make_schema_graph():
    """
    Build a small fixed schema graph like Neo4j's db.schema.visualization():
    Book in the center, connected to Author, Publisher, Season, ListWeek.
    """
    net = Network(height="350px", width="100%", bgcolor="white", font_color="black")
    net.toggle_physics(False)  # keep it static

    # Fixed positions for a clean schema look
    net.add_node("Book", label="Book", color=COLOR_MAP["Book"], x=0, y=0, physics=False)
    net.add_node("Author", label="Author", color=COLOR_MAP["Author"], x=200, y=0, physics=False)
    net.add_node("Publisher", label="Publisher", color=COLOR_MAP["Publisher"], x=-200, y=0, physics=False)
    net.add_node("Season", label="Season", color=COLOR_MAP["Season"], x=-100, y=150, physics=False)
    net.add_node("ListWeek", label="ListWeek", color=COLOR_MAP["ListWeek"], x=100, y=150, physics=False)

    # Relationship arrows
    net.add_edge("Author", "Book", title="WROTE", label="WROTE")
    net.add_edge("Publisher", "Book", title="PUBLISHED", label="PUBLISHED")
    net.add_edge("Book", "Season", title="PUBLISHED_IN", label="PUBLISHED_IN")
    net.add_edge("Book", "ListWeek", title="APPEARED_ON", label="APPEARED_ON")

    net.set_options("""
    var options = {
      "nodes": {"shape": "dot", "size": 22},
      "edges": {"arrows": {"to": {"enabled": true}}, "smooth": false},
      "physics": {"enabled": false}
    }
    """)
    return net


def main():
    # ---------- HEADER ----------
    st.title("NYT Book Bestsellers - Graph Overview (Neo4j)")
    st.markdown(
        """
        This app shows how **books** from the New York Times Bestseller lists connect to their  
        **authors**, **publishers**, **seasons**, and **weekly list appearances**.
        """
    )

    node_overview, rel_overview = get_overview()

    # ---------- SIDEBAR ----------
    st.sidebar.header("Legend")

    st.sidebar.subheader("Node types")
    for row in node_overview:
        label = row["label"]
        color = COLOR_MAP.get(label, "#333333")
        st.sidebar.markdown(
            f"<span style='color:{color}; font-size: 20px;'>●</span> &nbsp; **{label}**",
            unsafe_allow_html=True,
        )

    st.sidebar.subheader("Relationship types")
    for row in rel_overview:
        st.sidebar.write(f"• {row['rel_type']}")

    st.sidebar.markdown("---")
    limit = st.sidebar.slider(
        "Number of connections to visualize",
        min_value=50,
        max_value=500,
        value=350,
        step=50,
        help="Higher values show more of the graph but can look busier.",
    )

    # ---------- SCHEMA GRAPH (like db.schema.visualization) ----------
    st.subheader("Data model overview")
    st.markdown(
        "This schematic view mirrors **Neo4j's schema visualization**: "
        "a single `Book` node connected to the key context nodes."
    )
    schema_net = make_schema_graph()
    schema_html_file = "schema_graph.html"
    schema_net.save_graph(schema_html_file)
    with open(schema_html_file, "r", encoding="utf-8") as f:
        schema_html = f.read()
    components.html(schema_html, height=350, scrolling=False)

    st.markdown("...")

    # ---------- MAIN INTERACTIVE GRAPH ----------
    st.subheader("Interactive graph of real NYT bestsellers")

    nodes, edges = fetch_graph(limit=limit)

    col1, col2 = st.columns([3, 1])
    with col1:
        net = make_pyvis_graph(nodes, edges)
        html_file = "graph_books.html"
        net.save_graph(html_file)
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()
        components.html(html, height=650, scrolling=True)

    with col2:
        st.subheader("Summary")
        st.metric("Nodes in view", len(nodes))
        st.metric("Relationships in view", len(edges))
        st.markdown(
            """
            **How to read this:**
            - Purple = Books  
            - Blue = Authors  
            - Orange = Publishers  
            - Pink/Red = Weekly lists  
            - Teal = Seasons  

            Hover over any node to see details like title, publisher,
            list week, or season.
            """
        )


if __name__ == "__main__":
    main()