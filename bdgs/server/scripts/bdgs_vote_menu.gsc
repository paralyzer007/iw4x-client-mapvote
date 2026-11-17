/*
	BDGS map vote - thumbnail menu for players running the BDGS IW4x client.

	Players whose client loaded zone\dlc\bdgs_vote.ff send "bdgs_thumbs 1" in their
	userinfo. They get the picture menu (bdgs_vote.menu). Everyone else keeps the
	normal BDGS text vote - nothing changes for them.

	No fs_game mod is involved, so player stats and custom classes are untouched.

	REQUIRES the server to run the BDGS iw4x.dll (it adds the GetUserInfo method).
	On a stock iw4x.dll this file fails to compile and stops ALL scripts, so test
	it on a second server port first.

	How your vote script uses it (one tally, two ways to vote):

		// at vote start, for every player
		if ( player scripts\bdgs_vote_menu::hasThumbVote() )
			player scripts\bdgs_vote_menu::openThumbVote( maps, names, "Vote for the next map" );
		else
			... your existing text vote for this player ...

		// thumbnail votes arrive as:  level waittill( "bdgs_vote_pick", player, index );
		// index is 0-5, same order as the maps array you passed

		// whenever your tally changes
		scripts\bdgs_vote_menu::updateThumbVotes( counts );          // counts[0..5]
		scripts\bdgs_vote_menu::updateThumbText( "Vote (" + secs + "s):" );

		// at the end
		scripts\bdgs_vote_menu::showThumbWinner( winnerMap, winnerName );
		wait 3;
		scripts\bdgs_vote_menu::closeThumbVote();

	Menu, images and material template: "IW4x Post Map Vote Modified" by fella_guy,
	based on the Map Vote Menu Mod by |UzD|GaZa.
*/

init()
{
	precacheMenu( "bdgs_vote" );
	level.bdgsTileCount = 6; // tiles in bdgs_vote.menu
	level.bdgsThumbMaps = scripts\bdgs_thumbs_list::get();
	level.bdgsThumbVoters = [];
	level thread onPlayerConnect();
}

onPlayerConnect()
{
	for ( ;; )
	{
		level waittill( "connected", player );
		player setClientDvar( "ui_inVote", "0" );
		player setClientDvar( "hud_ShowWinner", "0" );
		player setClientDvar( "ui_selected_vote", "" );
	}
}

// true when this player's client has the thumbnail files loaded
hasThumbVote()
{
	return self GetUserInfo( "bdgs_thumbs" ) == "1";
}

// material for a map, or the "custom map" placeholder when we have no picture
thumbFor( mapname )
{
	if ( isDefined( level.bdgsThumbMaps[ toLower( mapname ) ] ) )
		return "preview_" + toLower( mapname );

	return "preview_custom_map";
}

// maps:  array of map names (mp_rust, ...), up to 6
// names: array of display names, same order
openThumbVote( maps, names, text )
{
	self endon( "disconnect" );

	self closeMenus();
	self setClientDvar( "hud_ShowWinner", "0" );
	self setClientDvar( "ui_selected_vote", "" );
	self setClientDvar( "hud_voteText", text );
	self setClientDvar( "hud_gamesize", level.players.size );

	for ( i = 0; i < level.bdgsTileCount; i++ )
	{
		if ( i < maps.size )
		{
			self setClientDvar( "hud_picName" + i, thumbFor( maps[ i ] ) );
			self setClientDvar( "hud_mapName" + i, names[ i ] );
		}
		else
		{
			self setClientDvar( "hud_picName" + i, "black" );
			self setClientDvar( "hud_mapName" + i, "" );
		}
		self setClientDvar( "hud_mapVotes" + i, "0" );
	}

	self setClientDvar( "ui_inVote", "1" );
	self openMenu( "bdgs_vote" );

	level.bdgsThumbVoters[ level.bdgsThumbVoters.size ] = self;
	self.bdgsTileCount = maps.size;
	self thread watchThumbVote();
}

watchThumbVote()
{
	self endon( "disconnect" );
	level endon( "bdgs_vote_closed" );

	for ( ;; )
	{
		self waittill( "menuresponse", menu, response );

		if ( menu != "bdgs_vote" )
			continue;

		if ( !isSubStr( response, "map" ) )
			continue;

		index = int( getSubStr( response, 3 ) ) - 1;

		if ( index < 0 || index >= self.bdgsTileCount )
			continue;

		level notify( "bdgs_vote_pick", self, index );
	}
}

updateThumbVotes( counts )
{
	foreach ( player in thumbVoters() )
	{
		player setClientDvar( "hud_gamesize", level.players.size );

		for ( i = 0; i < counts.size && i < level.bdgsTileCount; i++ )
			player setClientDvar( "hud_mapVotes" + i, counts[ i ] );
	}
}

updateThumbText( text )
{
	foreach ( player in thumbVoters() )
		player setClientDvar( "hud_voteText", text );
}

showThumbWinner( mapname, name )
{
	foreach ( player in thumbVoters() )
	{
		player setClientDvar( "hud_voteText", "^3Next Map:" );
		player setClientDvar( "hud_WinningName", thumbFor( mapname ) );
		player setClientDvar( "hud_WinningMap", name );
		player setClientDvar( "hud_ShowWinner", "1" );
	}
}

closeThumbVote()
{
	level notify( "bdgs_vote_closed" );

	foreach ( player in thumbVoters() )
	{
		player closeMenu( "bdgs_vote" );
		player setClientDvar( "ui_inVote", "0" );
		player setClientDvar( "hud_ShowWinner", "0" );
		player setClientDvar( "ui_selected_vote", "" );
	}

	level.bdgsThumbVoters = [];
}

// players who opened the thumbnail vote and are still connected
thumbVoters()
{
	alive = [];

	foreach ( player in level.bdgsThumbVoters )
	{
		if ( isDefined( player ) )
			alive[ alive.size ] = player;
	}

	level.bdgsThumbVoters = alive;
	return alive;
}
