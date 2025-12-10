# category_tree
Category tree 

1. Clone project
```
git clone git@github.com:bsdemon/category_tree.git
```

2. Install depencies
```
uv sync
```

3. Activate virtual environment
```
source .venv/bin/activate
```

4. Apply migrations
```
uv run src/manage.py migrate
```

5. Optionaly you can seed database with 2000 categoties and create 200000 similarities
Also you can edit seed_cathegories and generate_similarities to change settings on seeded data. 
```
uv run src/manage.py seed_categories
uv run src/manage.py generate_similarities
```

6. Finaly you can run script to analyze tree and get "rabit_holes" and "islands"
```
uv run src/manage.py analyze_similarities
```

7. OPEN API docs
```
http://localhost:8000/api/docs
```