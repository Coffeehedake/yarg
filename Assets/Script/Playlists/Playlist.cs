using System;
using System.Collections.Generic;
using YARG.Core.Song;
using YARG.Song;

namespace YARG.Playlists
{
    public class Playlist
    {
        /// <summary>
        /// The display name of the playlist.
        /// </summary>
        public string Name;

        /// <summary>
        /// The author of the playlists.
        /// </summary>
        public string Author;

        /// <summary>
        /// The unique ID of the playlist.
        /// </summary>
        public Guid Id;

        /// <summary>
        /// The song hashes within the playlist.
        /// </summary>
        public List<HashWrapper> SongHashes;
        public readonly bool Ephemeral;

        public int Count => SongHashes.Count;

        /// <summary>
        /// Raised after each editing call on this class, even one that changes nothing (such as removing a song
        /// that isn't there); <see cref="Clear"/> raises it only when it removed something.
        /// Writes straight to <see cref="SongHashes"/> don't raise it.
        /// </summary>
        public event Action Edited;

        public Playlist(bool ephemeral)
        {
            Ephemeral = ephemeral;
            SongHashes = new List<HashWrapper>();
            Author = "You";
            Name = "Setlist";
            Id = Guid.NewGuid();
        }

        public Playlist() {}

        public void AddSong(SongEntry song)
        {
            if (!ContainsSong(song))
            {
                SongHashes.Add(song.Hash);
                OnEdited();
            }
        }

        public void RemoveSong(SongEntry song)
        {
            SongHashes.Remove(song.Hash);
            OnEdited();
        }

        public bool ContainsSong(SongEntry song)
        {
            return SongHashes.Contains(song.Hash);
        }

        public List<SongEntry> ToList()
        {
            var songlist = new List<SongEntry>();

            foreach (var hash in SongHashes)
            {
                if (SongContainer.SongsByHash.TryGetValue(hash, out var song))
                {
                    songlist.Add(song[0]);
                }
            }

            return songlist;
        }

        public void MoveSongUp(SongEntry song)
        {
            // Get the index of the song
            var index = SongHashes.IndexOf(song.Hash);

            // If the song is not at the top, swap it with the previous song
            if (index > 0)
            {
                (SongHashes[index - 1], SongHashes[index]) = (SongHashes[index], SongHashes[index - 1]);
                OnEdited();
            }
        }

        public void MoveSongDown(SongEntry song)
        {
            // Get the index of the song
            var index = SongHashes.IndexOf(song.Hash);

            // If the song is not at the bottom, swap it with the next song
            if (index < SongHashes.Count - 1)
            {
                (SongHashes[index + 1], SongHashes[index]) = (SongHashes[index], SongHashes[index + 1]);
                OnEdited();
            }
        }

        /// <summary>
        /// Replaces the contents in one step, raising <see cref="Edited"/> exactly once.
        ///
        /// For the reorderings <see cref="MoveSongUp"/> and <see cref="MoveSongDown"/> cannot
        /// express, because they move one place: inserting at a position, or sorting part of the
        /// list. Doing those as a <see cref="Clear"/> plus a run of <see cref="AddSong"/> calls is
        /// fine on a setlist nobody is playing, but during a show it empties the list the playback
        /// position points into and raises an <see cref="Edited"/> per song, so every subscriber
        /// sees a list that is briefly wrong. This exposes no intermediate state.
        ///
        /// Duplicates are dropped, keeping the first, because <see cref="AddSong"/> does not allow
        /// a song in twice and a list that came through here should not differ from one built with it.
        /// </summary>
        public void ReplaceSongs(IEnumerable<HashWrapper> hashes)
        {
            if (hashes == null)
            {
                return;
            }

            var replacement = new List<HashWrapper>();
            foreach (var hash in hashes)
            {
                if (!replacement.Contains(hash))
                {
                    replacement.Add(hash);
                }
            }

            // In place rather than assigning a new list: SongHashes is a public field, and
            // anything holding a reference to it would keep reading the old contents.
            SongHashes.Clear();
            SongHashes.AddRange(replacement);
            OnEdited();
        }

        public void Clear()
        {
            if (SongHashes.Count == 0)
            {
                return;
            }

            SongHashes.Clear();
            Edited?.Invoke();
        }

        public void SortByName(bool ascending = true)
        {
            // Get all songs, sort by name, then rebuild hash list
            var songs = ToList();
            songs.Sort((a, b) => CompareSongsByName(a, b, ascending));

            SongHashes.Clear();
            foreach (var song in songs)
            {
                SongHashes.Add(song.Hash);
            }

            OnEdited();
        }

        public void SortByArtist(bool ascending = true)
        {
            // Get all songs, sort by artist, then rebuild hash list
            var songs = ToList();
            songs.Sort((a, b) => CompareSongsByArtist(a, b, ascending));

            SongHashes.Clear();
            foreach (var song in songs)
            {
                SongHashes.Add(song.Hash);
            }

            OnEdited();
        }

        private void OnEdited()
        {
            if (!Ephemeral)
            {
                PlaylistContainer.RemoveDeadHashes(this, SongContainer.SongsByHash);
                PlaylistContainer.SavePlaylist(this);
            }

            Edited?.Invoke();
        }

        private static int CompareSongsByName(SongEntry lhs, SongEntry rhs, bool ascending)
        {
            int result = CompareSortStrings(lhs.Name, rhs.Name);
            if (result == 0)
            {
                result = CompareSortStrings(lhs.Artist, rhs.Artist);
            }
            if (result == 0)
            {
                result = lhs.SortBasedLocation.CompareTo(rhs.SortBasedLocation);
            }

            return ascending ? result : -result;
        }

        private static int CompareSongsByArtist(SongEntry lhs, SongEntry rhs, bool ascending)
        {
            int result = CompareSortStrings(lhs.Artist, rhs.Artist);
            if (result == 0)
            {
                result = CompareSortStrings(lhs.Name, rhs.Name);
            }
            if (result == 0)
            {
                result = lhs.SortBasedLocation.CompareTo(rhs.SortBasedLocation);
            }

            return ascending ? result : -result;
        }

        private static int CompareSortStrings(SortString lhs, SortString rhs)
        {
            int result = lhs.CompareTo(rhs);
            if (result == 0)
            {
                result = string.Compare(lhs.Original, rhs.Original, StringComparison.OrdinalIgnoreCase);
            }

            return result;
        }
    }
}
