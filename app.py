from flask import Flask, request, jsonify, render_template, flash, send_file
import openai
import io
import csv
from elasticsearch import Elasticsearch

app = Flask(__name__)
openai.api_key = "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"

# 创建 Elasticsearch 实例
es = Elasticsearch("http://localhost:9200")

# 创建 Elasticsearch 索引
es.indices.create(index='notes', ignore=400)

notes = [
    {
        'title': 'First Note',
        'content': 'This is the content of the first note.'
    },
    {
        'title': 'Second Note',
        'content': 'This is the content of the second note.'
    }
]

# 将现有笔记添加到 Elasticsearch 索引中
for note_id, note in enumerate(notes):
    es.index(index='notes', id=note_id, document=note)

@app.route('/notes/<int:note_id>')
def note_detail(note_id):
    print(note_id)
    note = notes[note_id]
    return render_template('note_detail.html', note=note)

@app.route('/notes', methods=['POST'])
def add_note():

    note = request.json
    notes.append(note)
    note_id=len(notes)-1
    es.index(index='notes',id=note_id,document=note)
    print(notes)
    return jsonify(note), 201



@app.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    if 0 <= note_id < len(notes):
        deleted_note = notes.pop(note_id)
        es.delete(index='notes',id=note_id)

        return jsonify(deleted_note), 200
    else:
        return jsonify({"error": "Note not found"}), 404

@app.route('/notes/<int:note_id>', methods=['PUT'])
def modify_note(note_id):
    if 0 <= note_id < len(notes):
        note = request.json
        notes[note_id] = note
        es.index(index='notes',id=note_id,document=note)

        return jsonify(note), 200
    else:
        return jsonify({"error": "Note not found"}), 404

@app.route('/analyze', methods=['POST'])
def analyze_notes():
    data=request.json
    if not data or 'content' not in data:
        return jsonify({"error": "Missing content in request data"}), 400
    content = data['content']

    print(content)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": f"{content}"}
        ]
    )
    # response.choices[0].message.content
    result=response.choices[0].message.content
    print(result)
    return jsonify({"content": result}), 200



@app.route('/notes', methods=['GET'])
def search_notes():
    keyword = request.args.get('keyword', '').lower()
    filtered_notes = [note for note in notes if
                      keyword in note['title'].lower() or keyword in note['content'].lower()]
    return jsonify(filtered_notes)



@app.route('/download_note/<int:note_id>', methods=['GET'])
def download_note(note_id):
    if 0 <= note_id < len(notes):
        note = notes[note_id]
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)

        writer.writerow(['Title', 'Content'])
        writer.writerow([note['title'], note['content']])

        csv_data.seek(0)
        return send_file(csv_data, mimetype='text/csv', as_attachment=True, attachment_filename='note.csv')
    else:
        flash("Note not found.")
        return render_template('index.html', notes=notes)


@app.route('/upload_notes', methods=['POST'])
def upload_notes():
    data = request.json
    if not data or 'notes' not in data:
        return jsonify({"error": "Missing notes in request data"}), 400

    uploaded_notes = data['notes']
    if not isinstance(uploaded_notes, list):
        return jsonify({"error": "Invalid notes format"}), 400

    notes.extend(uploaded_notes)
    return jsonify({"message": "Notes uploaded successfully", "uploaded_notes": len(uploaded_notes)}), 200


@app.route('/')
def index():
    return render_template('index.html', notes=notes)



# 新的搜索路由
@app.route('/search_notes', methods=['GET'])
def search_notes_es():
    keyword = request.args.get('keyword', '').lower()
    print(keyword)
    if not keyword:
        return jsonify({"error": "Missing keyword in request"}), 400

    search_body = {
        "query": {
            "multi_match": {
                "query": keyword,
                "fields": ["title", "content"]
            }
        }
    }

    search_results = es.search(index='notes', body=search_body)

    print(search_results)
    hits = search_results['hits']['hits']
    filtered_notes = [hit['_source'] for hit in hits]

    return jsonify(filtered_notes)

if __name__ == '__main__':
    app.run(debug=True)