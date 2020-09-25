from __future__ import print_function
import pickle
import os.path
import json
import sqlite3
import sys
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive']


def build_query(folders):
    query = ""
    for f in folders:
        if query != "":
            query = query + " or '{}' in parents".format(f)
        else:
            query = "('{}' in parents".format(f)
    query = query + ")  and trashed=false"
    return query


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "full":
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('drive', 'v3', credentials=creds)
        page_token = None
        counter = 0
        file_list = []
        while True:
            response = service.files().list(q="trashed=false",
                                            pageSize=1000,
                                            corpora='teamDrive',
                                            supportsTeamDrives=True,
                                            includeTeamDriveItems=True,
                                            teamDriveId='{TEAMDRIVE_ID}',
                                            fields='nextPageToken, files(id, name, parents)',
                                            pageToken=page_token).execute()
            page_token = response.get('nextPageToken', None)
            files = response.get('files', None)
            counter = counter + len(files)
            for f in files:
                file_list.append(f)
            if page_token is None:
                break
            print(counter)

        movie_id = "{MOVIE_FOLDER_ID}"

        id_to_name = {}
        movie_struct = {}

        for d in file_list:
            id_to_name[d["id"]] = d["name"]
            if movie_id in d["parents"]:
                movie_struct[d["id"]] = []

        movie_keys = movie_struct.keys()
        for d in file_list:
            if d["parents"][0] in movie_keys:
                movie_struct[d["parents"][0]].append(d["name"])

        with open('id_to_name.txt', 'w') as fout:
            json.dump(id_to_name, fout)

        with open('movie_struct.txt', 'w') as fout:
            json.dump(movie_struct, fout)

    with open('movie_struct.txt') as json_file:
        movie_struct = json.load(json_file)
    with open('id_to_name.txt') as json_file:
        id_to_name = json.load(json_file)

    paths_gdrive = []
    paths_radarr = []

    for id, files in movie_struct.items():
        path = id_to_name[id]
        for file in files:
            paths_gdrive.append(path + "/" + file)

    dbs = ["{RADARR_DB_PATH}"]

    for db in dbs:
        conn = sqlite3.connect(db)
        conn.row_factory = lambda cursor, row: [row[0], row[1]]
        c = conn.cursor()
        rows = c.execute("""
        SELECT movies.Path, MovieFiles.RelativePath
        FROM movies
        INNER JOIN MovieFiles on MovieFiles.MovieId = movies.id
        """).fetchall()

        for row in rows:
            paths_radarr.append(row[0].replace("/mnt/unionfs/Media/Movies/", "") + "/" + row[1])

    print(len(paths_gdrive))

    print("Not in radarr:")
    counter = 0
    for p in paths_gdrive:
        if p not in paths_radarr:
            counter += 1
            try:
                print("\t/mnt/unionfs/Media/Movies/" + p)
            except FileNotFoundError:
                continue
    print(counter)



    print("Not in gdrive:")
    for p in paths_radarr:
        if "The High Note" in p:
            print(p)
        if p not in paths_gdrive:
            print("\t/mnt/unionfs/Media/Movies/" + p)


if __name__ == '__main__':
    main()
