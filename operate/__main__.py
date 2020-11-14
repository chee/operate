import os
from os.path import basename
from subprocess import PIPE, Popen
from slugify import slugify
from PyInquirer import prompt
from argparse import ArgumentParser
from os import makedirs, path
from shutil import copyfile
from pydub import AudioSegment
from .upload import upload
from signal import signal, SIGINT
from sys import exit
from datetime import date

parser = ArgumentParser()

parser.add_argument("-d", "--disk",
                    help="where the op-1 lives",
                    default="/home/chee/disks/54FF-1FEE")

parser.add_argument("-m", "--music",
                    help="where the music goes on the computer",
                    default="/home/chee/electro/op1")

parser.add_argument("-a", "--artist",
                    help="artist (for id3)",
                    default="quiet party")

args = parser.parse_args()


class MusicPlace():
    def __init__(self, dir):
        self.dir = dir
        self.song = SongDir(self.dir)
        self.synth = InstrumentDir(self.dir, "synth")
        self.drum = InstrumentDir(self.dir, "drum")
    def make_song(self, slug):
        return Song(self.song.dir, slug)

class InstrumentDir():
    def __init__(self, root_dir: str, type: str):
        self.type = type
        self.dir = path.join(root_dir, type)
        self.snapshot = path.join(self.dir, "snapshot")
        self.user = path.join(self.dir, "user")
    def patch(self, collection, name):
        return path.join(self.dir, collection, name)
    def collection_names(self):
        return map(lambda ent : ent.name, os.scandir(self.dir))
    def patch_names(self, collection):
        return map(lambda ent : ent.name, os.scandir(path.join(self.dir, collection)))
    def copy_dir_to(self, dir, destination, recursive=True, prefix="", target_collection=dir):
        dest_sub = path.join(destination.dir, target_collection)
        makedirs(dest_sub, exist_ok=True)
        for ent in os.scandir(path.join(self.dir, dir)):
            if ent.is_dir() and recursive:
                self.copy_dir_to(path.join(dir, ent.name), destination, recursive, prefix, target_collection)
            elif ent.is_file():
                copy(ent.path, path.join(dest_sub, f"{prefix}{ent.name}"))
    def backup_user(self, destination):
        self.copy_dir_to("user", destination, False)
    def backup_snapshots(self, destination):
        self.copy_dir_to("snapshot", destination, False)
    def remove(self, collection, name):
        os.remove(self.patch(collection, name))
    def save_item_to(self, source_collection, source_name, target_instrument, target_collection, target_name):
        source = self.patch(source_collection, source_name)
        target_dir = path.join(target_instrument.dir, target_collection)
        target = path.join(target_dir, target_name)
        makedirs(target_dir, exist_ok=True)
        copy(source, target)

class Operator():
    def __init__(self, dir):
        if not path.exists(dir):
            print(f"operator not found at {dir}")
            exit(1)
        self.dir = dir
        self.side_a = path.join(dir, "album", "side_a.aif")
        self.side_b = path.join(dir, "album", "side_b.aif")
        self.tape = Tape(dir)
        self.synth = InstrumentDir(dir, "synth")
        self.drum = InstrumentDir(dir, "drum")
        if not path.exists(self.tape.dir) or not path.exists(self.synth.dir) or not path.exists(self.drum.dir):
            print(f"operator not found at {dir}")
            exit(1)

class Tape():
    def __init__(self, root_dir):
        self.dir = path.join(root_dir, "tape")
        self.track_1 = path.join(self.dir, "track_1.aif")
        self.track_2 = path.join(self.dir, "track_2.aif")
        self.track_3 = path.join(self.dir, "track_3.aif")
        self.track_4 = path.join(self.dir, "track_4.aif")
        self.tracks = [
            self.track_1,
            self.track_2,
            self.track_3,
            self.track_4
        ]
    def mkdir(self):
        makedirs(self.dir, exist_ok=True)
    def copy_to(self, destination):
        copy(self.track_1, destination.track_1)
        copy(self.track_2, destination.track_2)
        copy(self.track_3, destination.track_3)
        copy(self.track_4, destination.track_4)


class Song():
    def __init__(self, song_dir, slug):
        self.slug = slug
        self.dir = path.join(song_dir, slug)
        self.aif = path.join(self.dir, f"{slug}.aif")
        self.mp3 = path.join(self.dir, f"{slug}.mp3")
        self.tape = Tape(self.dir)
        self.synth = InstrumentDir(self.dir, "synth")
        self.drum = InstrumentDir(self.dir, "drum")
    def mkdir(self):
        makedirs(self.dir, exist_ok=True)
    def has_tape(self):
        return path.exists(self.tape.dir)


class SongDir():
    def __init__(self, music_dir):
        self.dir = path.join(music_dir, "song")
    def list(self):
        return map(lambda ent : Song(self.dir, ent.name),
                   os.scandir(self.dir))
    def paths(self):
        return map(lambda song : song.slug, self.list())
    def paths_with_tapes(self):
        return map(lambda song : song.slug,
                   filter(lambda song : song.has_tape(),
                          self.list()))


def copy(source: str, target: str):
    print(f"copying {source} to {target}")
    copyfile(source, target)


def get_side(operator: Operator):
    return prompt([
        {
            'type': 'list',
            'name': 'side',
            'message': 'pick a side',
            'choices': [
                {
                    'name': 'side_a.aif',
                    'value': operator.side_a
                },
                {
                    'name': 'side_b.aif',
                    'value': operator.side_b
                }
            ]
        }
    ])['side']

def good_menu():
    return prompt({
        'type': 'list',
        'name': 'op',
        'message': 'good?',
        'choices': ['again', 'yes', 'no']
    })['op']

def preview_menu(source, should_preview=False):
    should_preview = should_preview or prompt({
        'type': 'confirm',
        'name': 'preview',
        'message': 'preview?'
    })['preview']
    if should_preview:
        music = Popen(["mpv", source], stdout=PIPE)
        op = good_menu()
        if op == 'again':
            music.terminate()
            return preview_menu(source, should_preview=True)
        elif op == 'yes':
            music.terminate()
            return True
        elif op == 'no':
            music.terminate()
            return False
    else:
        return True

def albums_menu(operator: Operator, place: MusicPlace, op):
    if op == "cancel":
        return
    if op == "save":
        side = get_side(operator)
        source = side
        ok = preview_menu(source)
        if not ok:
            return albums_menu(operator, place, op)
        answers = prompt([
            {
                'type': 'input',
                'name': 'title',
                'message': 'title (will be slugified for filename)',
            },
            {
                'type': 'confirm',
                    'name': 'bring_tape?',
                'message': 'bring tape? (will be stored alongside)'
            },
            {
                'type': 'confirm',
                    'name': 'bring_instruments?',
                'message': 'bring user instruments?'
            },
            {
                'type': 'confirm',
                'name': 'upload?',
                'message': 'upload? (to chee@snoot.club:music)'
            }
        ])
        title = answers['title']
        artist = args.artist
        slug = slugify(title)
        song = place.make_song(slug)
        song.mkdir()
        # copy the song over
        target = song.aif
        copy(source, target)
        # now let's make the mp3
        print(f"converting {basename(song.aif)} to {basename(song.mp3)}")
        audio = AudioSegment.from_file(song.aif, format="aiff")
        audio.export(song.mp3,
                     format="mp3",
                     tags={
                         'title': title,
                         'artist': artist
                     })
        # well that was straight-forward
        if answers['upload?']:
            upload(song.mp3)
        if answers['bring_tape?']:
            song.tape.mkdir()
            operator.tape.copy_to(song.tape)
        if answers['bring_instruments?']:
            operator.synth.backup_snapshots(song.synth)
            operator.synth.backup_user(song.synth)
            operator.drum.backup_snapshots(song.drum)
            operator.drum.backup_user(song.drum)
    elif op == "restore":
        desired_song = prompt(
            {
                'type': 'list',
                'name': 'song',
                'message': 'pick a song',
                'choices': list(place.song.paths())
            }
        )['song']
        desired_side = get_side(operator)
        source = Song(place.song.dir, desired_song).aif
        target = desired_side
        copy(source, target)


def tapes_menu(operator: Operator, place: MusicPlace, op):
    if op == "cancel":
        return
    if op == "save":
        title = prompt({
            'type': 'input',
            'name': 'title',
            'message': 'title (will be slugified for filename)',
        })['title']
        slug = slugify(title)
        song = place.make_song(slug)
        song.tape.mkdir()
        operator.tape.copy_to(song.tape)
    elif op == "restore":
        desired_song = prompt({
                'type': 'list',
                'name': 'song',
                'message': 'pick a song',
                'choices': list(place.song.paths_with_tapes())
        })['song']
        song = place.make_song(desired_song)
        song.tape.copy_to(operator.tape)


def instrument_menu(operator_instrument: InstrumentDir, place_instrument: InstrumentDir, op):
    if op == "cancel":
        return
    if op == "save":
        collection_choices = list(operator_instrument.collection_names())
        collection = prompt({
            'type': 'list',
            'name': 'collection',
            'message': 'from which collection?',
            'choices': collection_choices
        })['collection']
        patch_choices = list(operator_instrument.patch_names(collection))
        patch_choices.append("all of them!")
        patch = prompt({
                'type': 'list',
                'name': 'patch',
                'message': 'pick a patch',
                'choices': patch_choices
        })['patch']
        if patch == "all of them!":
            save_as = prompt([
                {
                    'type': 'input',
                    'name': 'collection',
                    'message': 'save in',
                    'default': "chee" if collection == "user" else collection
                },
                {
                    'type': 'input',
                    'name': 'prefix',
                    'message': 'prefix',
                    'default': date.today().strftime('%Y%m%d'),
                    'when': lambda _ : collection == "user"
                }
            ])

            prefix = f"{save_as['prefix']}-" if collection == "user" else ""

            return operator_instrument.copy_dir_to(
                collection,
                place_instrument,
                prefix=prefix,
                target_collection=save_as['collection'])

        ok = preview_menu(operator_instrument.patch(collection, patch))
        if not ok:
            return instrument_menu(operator_instrument, place_instrument, op)
        save_as = prompt([
            {
                'type': 'input',
                'name': 'collection',
                'message': 'save in',
                'default': "chee" if collection == "snapshot" else collection
            },
            {
                'type': 'input',
                'name': 'name',
                'message': 'save as',
                'default': patch
            }
        ])
        target_name = save_as['name']
        if not target_name.endswith(".aif"):
            target_name += ".aif"
        target_collection = save_as['collection']
        operator_instrument.save_item_to(collection, patch, place_instrument, target_collection, target_name)
        if collection == "snapshot":
            operator_instrument.remove(collection, patch)
            place_instrument.save_item_to(target_collection, target_name, operator_instrument, target_collection, target_name)
    if op == "restore":
        collection_choices = list(place_instrument.collection_names())
        collection_choices.append("from a song!")
        collection = prompt({
            'type': 'list',
            'name': 'collection',
            'message': 'from which collection?',
            'choices': collection_choices
        })['collection']
        patch_choices = list(place_instrument.patch_names(collection))
        patch_choices.append("all of them!")
        patch = prompt({
                'type': 'list',
                'name': 'patch',
                'message': 'pick a patch',
                'choices': patch_choices
        })['patch']
        if patch == "all of them!":
            return place_instrument.copy_dir_to(collection, operator_instrument)
        place_instrument.save_item_to(collection, patch, operator_instrument, collection, patch)


def synths_menu(operator: Operator, place: MusicPlace, op):
    instrument_menu(operator.synth, place.synth, op)


def drums_menu(operator: Operator, place: MusicPlace, op):
    instrument_menu(operator.drum, place.drum, op)


def get_op():
    return prompt({
        'type': 'list',
        'name': 'op',
        'message': 'what would you like to do?',
        'choices': ['save', 'restore', 'cancel']
    })['op']


def main():
    while True:
        operator = Operator(args.disk)
        place = MusicPlace(args.music)
        desired_menu = prompt({
            'type': 'list',
            'name': 'answer',
            'message': 'what would you like to work with?',
            'choices': ['albums', 'tapes', 'synths', 'drums', 'exit']
        })['answer']

        if desired_menu == 'albums':
            albums_menu(operator=operator,
                        place=place,
                        op=get_op())
        elif desired_menu == 'tapes':
            tapes_menu(operator=operator,
                       place=place,
                       op=get_op())
        elif desired_menu == 'synths':
            synths_menu(operator=operator,
                        place=place,
                        op=get_op())
        elif desired_menu == 'drums':
            drums_menu(operator=operator,
                       place=place,
                       op=get_op())
        elif desired_menu == 'exit':
            break

def silence(_, __):
    exit(0)

if __name__ == '__main__':
    signal(SIGINT, silence)
    try:
        main()
    except:
        exit(1)
