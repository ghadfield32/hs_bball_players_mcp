var Top_Player_Basketball = {
    TopPlayerFilter: function (sportcode, season) {
        $('#tdLeague').html("");
        $('#tdCategor').html("");
        var ajaxRequest;
        if (ajaxRequest != null)
            ajaxRequest.abort();
            var strLeg = new Sys.StringBuilder("");
            strLeg.append("<select id='drpLeague'>");
            strLeg.append("</select>");
            $('#tdLeague').html(strLeg.toString());
            Top_Player.bindLeagueForSport(sportcode, season);

        $('#lblLable').html('Division');
            $('#lblCategory').html('Category');
            $('#lblSeason').html('Season');
            var strCat = new Sys.StringBuilder("");
            strCat.append("<select id='drpCategor'>");
//            strCat.append("<option value='1' >Top Scorers</option>");
//            strCat.append("<option value='2' >Top Assists</option>");
//            strCat.append("<option value='3' >Top Rebounds</option>");
//            strCat.append("<option value='4' >Top Free Throw Percentage</option>");
//            strCat.append("<option value='5' >Top Scorers Per Game</option>");
//            strCat.append("<option value='6' >Top Assists Per Game</option>");
//            strCat.append("<option value='7' >Top Rebounds Per Game</option>");
            strCat.append("</select>");

            $('#tdCategor').append(strCat.toString());
            Top_Player.bindCategory(sportcode, season);

           // $('#tdCategor').html(strCat.toString());
    },

    GetTopPlayers: function (order, sportcode, season, league) {
        var str1;
        var ajaxRequest;
        if (ajaxRequest != null) {
            ajaxRequest.abort();
        }
        $('#imgProgressBar').css('display', 'block');
            if (order == 1) {
                ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetBskBallStats1?order=" + order + "&csports='" + sportcode + "' &season=" + season + "&league='" + league + "'", null,
                  				Top_Player_Basketball.getBskBallData);
            }
            if (order == 2) {
                ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetBskBallStats2?order=" + order + "&csports='" + sportcode + "' &season=" + season + "&league='" + league + "'", null,
                  				Top_Player_Basketball.getBskBallData);
            }
            if (order == 3) {
                ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetBskBallStats3?order=" + order + "&csports='" + sportcode + "' &season=" + season + "&league='" + league + "'", null,
                  				Top_Player_Basketball.getBskBallData);
            }
            if (order == 4) {
                ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetBskBallStats4?order=" + order + "&csports='" + sportcode + "' &season=" + season + "&league='" + league + "'", null,
                  				Top_Player_Basketball.getBskBallData);
            }
            if (order == 5) {
                ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetBskBallStats5?order=" + order + "&csports='" + sportcode + "' &season=" + season + "&league='" + league + "'", null,
                  				Top_Player_Basketball.getBskBallData);
            }
            if (order == 6) {
                ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetBskBallStats6?order=" + order + "&csports='" + sportcode + "' &season=" + season + "&league='" + league + "'", null,
                  				Top_Player_Basketball.getBskBallData);
            }
            if (order == 7) {
                ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetBskBallStats7?order=" + order + "&csports='" + sportcode + "' &season=" + season + "&league='" + league + "'", null,
                  				Top_Player_Basketball.getBskBallData);
            }
    },

    getBskBallData: function (data) {
        var colName;
        var sb = new Sys.StringBuilder("<table><thead><tr><td colspan=6 style='color:red;'>#Replace#</td></tr><tr><th>RANK</th><th>PLAYER</th><th>GRADE</th><th>SCHOOL</th>");

        if (order == 1)
            sb.append("<th>POINTS</th>");
        else if (order == 2)
            sb.append("<th>ASSISTS</th>");
        else if (order == 3)
            sb.append("<th>&nbsp;&nbsp;OFF</th><th>&nbsp;&nbsp;DEF</th><th>&nbsp;&nbsp;REBOUNDS</th>");
        else if (order == 4)
            sb.append("<th>&nbsp;&nbsp;FTMADE</th><th>&nbsp;&nbsp;FTATT</th><th>&nbsp;&nbsp;FREE THROW(%)</th>");
        else if (order == 5)
            sb.append("<th>&nbsp;&nbsp;Points</th><th>&nbsp;&nbsp;POINTS/GAME</th>");
        else if (order == 6)
            sb.append("<th>&nbsp;&nbsp;ASSISTS</th><th>&nbsp;&nbsp;ASSISTS/GAME</th>");
        else if (order == 7)
            sb.append("<th>&nbsp;&nbsp;Rebounds</th><th>&nbsp;&nbsp;REBOUNDS/GAME</th>");

        sb.append("<th>NO. OF GAMES</th></tr>");
        var pgrade;
        var rplc = '';
        var rank = 0, j = 1, prevpoints = 0, prevgames = 0, newPoints = 0, newGames = 0;
        if (data.d.length > 0) {

            $.each(data.d, function (i, player) {
                if (order == 1) {
                    newPoints = player.points;
                    rplc = '';
                }
                else if (order == 2) {
                    newPoints = player.assists;
                    rplc = '';
                }
                else if (order == 3) {
                    newPoints = player.trebounds;
                    rplc = '';
                }
                else if (order == 4) {
                    newPoints = player.per.toFixed(2);
                    rplc = 'Players are ranked based on at least 30 free throw attempts.';
                }
                else if (order == 5 || order == 6 || order == 7) {
                    newPoints = player.pergame.toFixed(2);
                    rplc = 'Players are ranked based on a 10 game minimum.';
                }
                newGames = player.games;
                if (i == 0)
                    rank = 1;
                else {
                    if (newPoints == prevpoints && newGames == prevgames)
                        rank = rank;
                    else
                        rank = i + 1;
                }
                sb = new Sys.StringBuilder(sb.toString().replace('#Replace#', rplc));

                pgrade = getgradetxt(player.cclass);

                if (i % 2 == 0)
                    sb.append("<tr><td>" + rank + "</td><td><a href='" + WEB_SERVICE_BASEURL + "/profiles/player-profile.aspx#" + player.playerid + "/" + ccport + "'>" + player.cfname + " " + player.clname + "</a></td><td>" + pgrade + "</td><td><a href='" + WEB_SERVICE_BASEURL + "/profiles/team-profile.aspx#" + ccport + "/" + player.cschool + "'>" + player.newname + "</a></td>");
                else
                    sb.append("<tr class='alt'><td>" + rank + "</td><td><a href='" + WEB_SERVICE_BASEURL + "/profiles/player-profile.aspx#" + player.playerid + "/" + ccport + "'>" + player.cfname + " " + player.clname + "</td><td>" + pgrade + "</td><td><a href='" + WEB_SERVICE_BASEURL + "/profiles/team-profile.aspx#" + ccport + "/" + player.cschool + "'>" + player.newname + "</a></td>");

                if (order == 1) {
                    sb.append("<td>" + player.points + "</td>");
                    prevpoints = player.points;
                }
                else if (order == 2) {
                    sb.append("<td>" + player.assists + "</td>");
                    prevpoints = player.assists;
                }
                else if (order == 3) {
                    sb.append("<td>" + player.orebounds + "</td><td>" + player.drebounds + "</td><td>" + player.trebounds + "</td>");
                    prevpoints = player.trebounds;
                }
                else if (order == 4) {
                    sb.append("<td>" + player.ftmade + "</td><td>" + player.ftatt + "</td><td>" + player.per.toFixed(2) + "</td>");
                    prevpoints = player.per.toFixed(2);
                }
                else if (order == 5) {
                    sb.append("<td>" + player.points + "</td><td>" + player.pergame.toFixed(2) + "</td>");
                    prevpoints = player.pergame.toFixed(2);
                }
                else if (order == 6) {
                    sb.append("<td>" + player.assists + "</td><td>" + player.pergame.toFixed(2) + "</td>");
                    prevpoints = player.pergame.toFixed(2);
                }
                else if (order == 7) {
                    sb.append("<td>" + player.trebounds + "</td><td>" + player.pergame.toFixed(2) + "</td>");
                    prevpoints = player.pergame.toFixed(2);
                }
                prevgames = player.games;

                sb.append("<td>" + player.games + "</td></tr>")

            });
        }
        else {
            sb = new Sys.StringBuilder(sb.toString().replace('#Replace#', rplc));
            sb.append("<tr><td colspan=7>No records found.</td></tr>");
        }
        sb.append("</tbody></table>");
        $('#top_player_list').html(sb.toString());
        $('#imgProgressBar').css('display', 'none');
    }
}