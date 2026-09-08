using Cysharp.Text;
using UnityEngine;
using YARG.Core.Game;
using YARG.Core.Song;
using YARG.Helpers;
using YARG.Player;
using YARG.Playlists;
using YARG.Scores;
using YARG.Song;
using YARG.Song.RemoteLibrary;

namespace YARG.Menu.MusicLibrary
{
    public enum HighScoreInfoMode
    {
        Stars,
        Score,
        Off
    }

    public class SongViewType : ViewType
    {
        public override BackgroundType Background => BackgroundType.Normal;

        public override bool UseAsMadeFamousBy => !SongEntry.IsMaster;

        public readonly SongEntry SongEntry;
        public override string StableId => _stableId;
        public string ContentStableId => _contentStableId;

        private readonly MusicLibraryMenu _musicLibrary;
        private readonly string _stableId;
        private readonly string _contentStableId;

        private bool _fetchedScores;
        private PlayerScoreRecord _playerScoreRecord;
        private GameRecord _bandScoreRecord;
        private ScoreContext _fetchedScoreContext;

        public SongViewType(MusicLibraryMenu musicLibrary, SongEntry songEntry, string context = "library")
        {
            _musicLibrary = musicLibrary;
            SongEntry = songEntry;
            _contentStableId = $"Song:{SongEntry.Hash}_{SongEntry.ActualLocation}";
            _stableId = $"Song:{context}:{_contentStableId}";
        }

        public override string GetPrimaryText(bool selected)
        {
            return FormatAs(SongEntry.Name, TextType.Primary, selected);
        }

        public override string GetSecondaryText(bool selected)
        {
            return WithServerBadge(
                FormatAs(SongEntry.Artist, TextType.Secondary, selected), SongEntry);
        }

        /// <summary>
        /// Marks a song that came from the song server mirror.
        /// </summary>
        /// <remarks>
        /// It rides on the ARTIST line rather than getting a control of its own, and that is
        /// a deliberate limit rather than a first draft. A real badge would be a new object
        /// on the song-row prefab, and a prefab change cannot be verified from batchmode -
        /// it can only be looked at. Rich text can, so this is the version of the feature
        /// that can be MEASURED, and it costs the player nothing to read.
        ///
        /// Static and pure on purpose: a SongViewType needs a MusicLibraryMenu to exist, so
        /// an instance method here would be untestable headless. This one takes the already
        /// formatted text and the entry, and a probe can call it against entries produced by
        /// a real scan of the real mirror folder.
        ///
        /// Known trade-off, stated rather than discovered later: a player whose whole library
        /// comes from one server sees the tag on every row, where it says nothing. It is small
        /// and dim for that reason. If that turns out to be the common case, the answer is a
        /// setting, not a louder badge.
        /// </remarks>
        public static string WithServerBadge(string secondaryText, SongEntry entry)
        {
            if (!MirroredSongs.IsMirrored(entry))
            {
                return secondaryText;
            }

            // Appended AFTER the formatted text, never inside it: FormatAs closes its own
            // <color> and <font-weight>, and nesting a second colour inside them would leave
            // the badge inheriting the artist's weight on some rows and not others.
            return ZString.Concat(secondaryText, BadgeMarkup);
        }

        /// <summary>The badge itself, so a probe can look for exactly this and nothing else.</summary>
        public const string BadgeMarkup =
            "  <size=75%><color=#7cc4ff88>\u25cf server</color></size>";

#nullable enable
        public override Sprite? GetIcon()
#nullable disable
        {
            return SongSources.SourceToIcon(SongEntry.Source);
        }

        public override string GetSideText(bool selected)
        {
            FetchHighScores();

            using var builder = ZString.CreateStringBuilder();

            // If non-null, band score is being requested
            if (_bandScoreRecord is not null)
            {
                builder.AppendFormat("{0:N0}", _bandScoreRecord.BandScore);
                return builder.ToString();
            }

            // Never played!
            if (_playerScoreRecord is null)
            {
                return string.Empty;
            }

            var scoreColor = _playerScoreRecord.IsFc ? "#ffd029" : "#ffffff";
            builder.AppendFormat("<mspace=.5em><color={1}>{0:N0}</color></mspace>",
                _playerScoreRecord.Score, scoreColor);
            return builder.ToString();
        }

        public override ScoreInfo? GetScoreInfo()
        {
            FetchHighScores();

            // Never played!
            if (_playerScoreRecord is null)
            {
                return null;
            }

            return new ScoreInfo
            {
                Score = _playerScoreRecord.Score,
                Difficulty = _playerScoreRecord.Difficulty,
                Percent = _playerScoreRecord.GetPercent(),
                Instrument = _playerScoreRecord.Instrument,
                IsFc = _playerScoreRecord.IsFc
            };
        }

        public override StarAmount? GetStarAmount()
        {
            FetchHighScores();

            return GetStarAmount(_playerScoreRecord, _bandScoreRecord);
        }

        public static StarAmount? GetStarAmountForSong(SongEntry songEntry)
        {
            FetchHighScores(songEntry, out var playerScoreRecord, out var bandScoreRecord);

            return GetStarAmount(playerScoreRecord, bandScoreRecord);
        }

#nullable enable
        private static StarAmount? GetStarAmount(
            PlayerScoreRecord? playerScoreRecord,
            GameRecord? bandScoreRecord)
#nullable disable
        {
            if (bandScoreRecord is not null)
            {
                return bandScoreRecord.BandStars;
            }

            return playerScoreRecord?.Stars;
        }

        public override FavoriteInfo GetFavoriteInfo()
        {
            return new FavoriteInfo
            {
                ShowFavoriteButton = true,
                IsFavorited = PlaylistContainer.FavoritesPlaylist.ContainsSong(SongEntry)
            };
        }

        public override void SecondaryTextClick()
        {
            base.SecondaryTextClick();
           _musicLibrary.SetSearchInput(SortAttribute.Artist, $"\"{SongEntry.Artist.SearchStr}\"");
        }

        public override void PrimaryButtonClick()
        {
            base.PrimaryButtonClick();

            if (PlayerContainer.Players.Count <= 0)
            {
                return;
            }

            // Reset library's main index so we don't return to the index set by play a show
            MusicLibraryMenu.ResetMainLibraryIndex();
            MusicLibraryMenu.SetReload(MusicLibraryReloadState.Partial);

            GlobalVariables.State.CurrentSong = SongEntry;
            // This just makes stuff in DifficultySelectMenu easier
            GlobalVariables.State.ShowSongs.Clear();
            GlobalVariables.State.ShowSongs.Add(SongEntry);
            GlobalVariables.State.PlayingAShow = false;

            MenuManager.Instance.PushMenu(MenuManager.Menu.DifficultySelect);
        }

        public override void IconClick()
        {
           _musicLibrary.SetSearchInput(SortAttribute.Source, $"\"{SongEntry.Source.SearchStr}\"");
        }

        public override void FavoriteClick()
        {
            base.FavoriteClick();

            var info = GetFavoriteInfo();

            if (!info.IsFavorited)
            {
                PlaylistContainer.FavoritesPlaylist.AddSong(SongEntry);
            }
            else
            {
                PlaylistContainer.FavoritesPlaylist.RemoveSong(SongEntry);

                // Refresh the view to update the filter results
                _musicLibrary.RefreshAndReselect();
            }

            _musicLibrary.RefreshSidebar();
        }

        public override void AddToPlaylist(Playlist playlist)
        {
            playlist.AddSong(SongEntry);
        }

        public override void RemoveFromPlaylist(Playlist playlist)
        {
            playlist.RemoveSong(SongEntry);

            // Refresh the view to update the filter results
            _musicLibrary.RefreshAndReselect();
        }

        private void FetchHighScores()
        {
            var context = ScoreContext.Capture();
            if (_fetchedScores && _fetchedScoreContext.Equals(context))
            {
                return;
            }

            FetchHighScores(SongEntry, out _playerScoreRecord, out _bandScoreRecord);
            _fetchedScoreContext = context;
            _fetchedScores = true;
        }

        private static void FetchHighScores(SongEntry songEntry, out PlayerScoreRecord playerScoreRecord, out GameRecord bandScoreRecord)
        {
            ScoreContainer.GetPreferredHighScoresForCurrentPlayers(
                songEntry.Hash, out playerScoreRecord, out bandScoreRecord);
        }
    }
}
