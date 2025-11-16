
var qstr;
var para;
var order;
var ccport;
var season1;
var league1;
var spname;
var quarter;
var routine;
$(document).ready(function () {

    //Get SportCode Sportname and season
    qstr = location.toString().split('#');
    para = qstr[1].toString().split('/');
    ccport = para[0];
    spname = para[1];
    season1 = getCurrentSeason();

    $('#tdSeason').html("");

    //For Valid sportcode getTopPlayers
    if (ccport.length == 3) {
        var ssn = season1;
        var ss1 = season1 - 1;
        var ss2 = season1 - 2;
        var ss3 = season1 - 3;
        var strblSeason = new Sys.StringBuilder("");

        strblSeason.append("<select id='drpSeason' style='width:100px;'>");
        strblSeason.append("<option value='" + ssn + "'>" + (ssn - 1) + "-" + ssn + "</option>");
        strblSeason.append("<option value='" + ss1 + "'>" + (ss1 - 1) + "-" + ss1 + "</option>");
        strblSeason.append("<option value='" + ss2 + "'>" + (ss2 - 1) + "-" + ss2 + "</option>");
        strblSeason.append("<option value='" + ss3 + "'>" + (ss3 - 1) + "-" + ss3 + "</option>");
        strblSeason.append("</select>");
        $('#tdSeason').html(strblSeason.toString());

        var strR = redirectRuleandReg(ccport);
        $('#btnRules').attr('href', strR);


        if (ccport != '030' && ccport != '031' && ccport != '078' && ccport != '079' && ccport != '032' && ccport != '033' && ccport != '034' && ccport != '035' && ccport != '070')
            Top_Player.GetSportWithSameNameData();

        Top_Player.TopPlayerFilter(ccport, season1);
    }
    else
        window.location = WEB_SERVICE_BASEURL + "default.aspx";
});


var Top_Player = {

    GetSportWithSameNameData: function () {
        var ajaxRequest;
        if (ajaxRequest != null) {
            ajaxRequest.abort();
        }
        ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetAllSportsWithSameName?csports='" + ccport + "'", null,
            Top_Player.getSportWithSameNameData);
    },

    getSportWithSameNameData: function (data) {
        var strHead = new Sys.StringBuilder("");
        if (data.d.length == 0)
            window.location.href = WEB_SERVICE_BASEURL + "default.aspx";
        $.each(data.d, function (i, sport) {
            var sname;
            if (i == 0)
                spname = $.trim(sport.cname);
            sname = getSportGenderClass(sport.gender, sport.cvarsity, sport.cid);

            if (ccport == sport.cid) {
                strHead.append("<li><a class='active' href='#" + sport.cid + "/" + spname + "' onclick=Top_Player.reLoadData('" + sport.cid + "',this);>" + sname + "</a></li>");
            }
            else
                strHead.append("<li><a href='#" + sport.cid + "/" + spname + "' onclick=Top_Player.reLoadData('" + sport.cid + "',this);>" + sname + "</a></li>");
        });
        $('div.standings-holder ul.tab-set').html("<li class='first-child' style='padding:0 9px 0 17px; color:#ed773d;background:#EDEFF3;'>" + spname + "</li>" + strHead.toString());
    },

    // Bind season, category and league dropdowns
    TopPlayerFilter: function (sportcode, season) {
        $('#tdLeague').html("");
        $('#tdCategor').html("");
        var ajaxRequest;
        if (ajaxRequest != null)
            ajaxRequest.abort();

        if (sportcode == '001' || sportcode == '002' || sportcode == '003' || sportcode == '004' || sportcode == '048' || sportcode == '049' || sportcode == '090' || sportcode == '091') {
            $.getScript("/scripts/Top_Players/Basketball.js", function () {
                Top_Player_Basketball.TopPlayerFilter(ccport, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        //sportId=072 is added to support the new sport - BOYS MPL for baseball
        else if (sportcode == '006' || sportcode == "072" || sportcode == '028' || sportcode == '022' || sportcode == '040' || sportcode == '045') {
            $.getScript("/scripts/Top_Players/Base_Soft_ball.js", function () {
                Top_Player_Base_Soft_ball.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '007' || sportcode == '018' || sportcode == '050') {
            $.getScript("/scripts/Top_Players/Bowling.js", function () {
                Top_Player_Bowling.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '010' || sportcode == '047') {
            $.getScript("/scripts/Top_Players/Golf.js", function () {
                Top_Player_Golf.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '011' || sportcode == '020') {
            $.getScript("/scripts/Top_Players/Handball.js", function () {
                Top_Player_Handball.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '012' || sportcode == '021' || sportcode == "073" || sportcode == "074" || sportcode == "075" || sportcode == "076" || sportcode == "077") {
            $.getScript("/scripts/Top_Players/Soccer.js", function () {
                Top_Player_Soccer.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '013' || sportcode == '023') {
            $.getScript("/scripts/Top_Players/Swimming.js", function () {
                Top_Player_Swimming.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '014' || sportcode == '024') {
            $.getScript("/scripts/Top_Players/Tennis.js", function () {
                Top_Player_Tennis.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '065' || sportcode == '066' || sportcode == '071') {
            $.getScript("/scripts/Top_Players/Table_Tennis.js", function () {
                Top_Player_Table_Tennis.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '067' || sportcode == '068') {
            $.getScript("/scripts/Top_Players/Badminton.js", function () {
                Top_Player_Badminton.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '016' || sportcode == '026' || sportcode == '038' || sportcode == '051') {
            $.getScript("/scripts/Top_Players/Volleyball.js", function () {
                Top_Player_Volleyball.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '036' || sportcode == '044' || sportcode == '053' || sportcode == '063') {
            $.getScript("/scripts/Top_Players/Lacrosse.js", function () {
                Top_Player_Lacrosse.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '037') {
            $.getScript("/scripts/Top_Players/Crew.js", function () {
                Top_Player_Crew.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '056') {
            $.getScript("/scripts/Top_Players/Cricket.js", function () {
                Top_Player_Cricket.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '057') {
            $.getScript("/scripts/Top_Players/DoubleDutch.js", function () {
                Top_Player_DoubleDutch.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '058' || sportcode == '059') {
            $.getScript("/scripts/Top_Players/Rugby.js", function () {
                Top_Player_Rugby.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '061') {
            $.getScript("/scripts/Top_Players/FlagFootball.js", function () {
                Top_Player_FlagFootball.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '008' || sportcode == '054' || sportcode == '055') {
            $.getScript("/scripts/Top_Players/Fencing.js", function () {
                Top_Player_Fencing.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '005' || sportcode == '027') {
            $.getScript("/scripts/Top_Players/Football.js", function () {
                Top_Player_Football.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '017' || sportcode == '064') {
            $.getScript("/scripts/Top_Players/Wrestling.js", function () {
                Top_Player_Wrestling.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '009' || sportcode == '019') {
            $.getScript("/scripts/Top_Players/Gymnastics.js", function () {
                Top_Player_Gymnastics.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '030' || sportcode == '031' || sportcode == '078' || sportcode == '079' || sportcode == '032' || sportcode == '033' || sportcode == '034' || sportcode == '035' || sportcode == '070') {
            $.getScript("/scripts/Top_Players/Track.js", function () {
                Top_Player_Track.TopPlayerFilter(sportcode, season);
                //Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
        else if (sportcode == '069') {
            $.getScript("/scripts/Top_Players/Stunt.js", function () {
                Top_Player_Stunt.TopPlayerFilter(sportcode, season);
                Top_Player.bindEventsFortopFilter();
                Top_Player.loadTopPlyers();
            });
        }
    },

    //call onchange events for season, category and league dropdowns
    bindEventsFortopFilter: function () {
        $('#drpLeague').change(function () {

            if (ccport == '030' || ccport == '031' || ccport == '078' || ccport == '079' || ccport == '032' || ccport == '033' || ccport == '034' || ccport == '035' || ccport == '070') {

            }
            else if (ccport == '009' || ccport == '019') {
                order = $('#drpLeague option:selected').val();
            }
            else {
                league1 = $('#drpLeague option:selected').val();
                if (ccport == '013' && ccport == '023')
                    order = $('#drpCategor option:selected').val().toString();
            }

            if (ccport == '069') {
                Top_Player.loadTopPlyers();
            }
            else {
                Top_Player.GetTopPlayers(order, ccport, season1, league1);
            }
        });

        $('#drpSeason').change(function () {
            season1 = $('#drpSeason option:selected').val();

            //sportId=072 is added to support the new sport - BOYS MPL for baseball
            if (ccport == '006' || ccport == "072" || ccport == '028' || ccport == '022' || ccport == '040' || ccport == '045' || ccport == '061' || ccport == '001' || ccport == '002' || ccport == '003' || ccport == '004' || ccport == '048' || ccport == '049' || ccport == '037' || ccport == '056' || ccport == '057' || ccport == '058' || ccport == '059' || ccport == '010' || ccport == '047' || ccport == '011' || ccport == '020' || ccport == '036' || ccport == '021' || ccport == '012' || ccport == "073" || ccport == "074" || ccport == "075" || ccport == "076" || ccport == "077" || ccport == '044' || ccport == '053' || ccport == '063' || ccport == '014' || ccport == '024' || ccport == '065' || ccport == '066' || ccport == '071' || ccport == '067' || ccport == '068' || ccport == '016' || ccport == '026' || ccport == '038' || ccport == '051' || ccport == '007' || ccport == '018' || ccport == '050' || ccport == '013' || ccport == '023' || ccport == '090' || ccport == '091') {

                Top_Player.bindLeagueForSport(ccport, season1);
            }

            //sportId=005 and 027 football boys varsity and football junior varisty division binding based on season

            if (ccport == '005' || ccport == "027") {
                Top_Player.bindDivisionForSports(ccport, season1);
            }

            //end logic for sportId=005 and 027 football boys varsity and football junior varisty division binding based on season   

            if (ccport == '069') {
                Top_Player.bindLeagueForSport(ccport, season1);
                // Top_Player.loadTopPlyers();
            }
            else {
                Top_Player.GetTopPlayers(order, ccport, season1, league1);
            }
        });
        $('#drpCategor').change(function () {
            if (ccport == '030' || ccport == '031' || ccport == '078' || ccport == '079' || ccport == '032' || ccport == '033' || ccport == '034' || ccport == '035' || ccport == '070') {

            }
            else if (ccport == '005' || ccport == '027' || ccport == '061') {
                if ($('#drpCategor option:selected').val() == '00')
                    alert('Please Select One Of The Sub categories.');
                else
                    order = $('#drpCategor option:selected').val();
            }
            else if (ccport == '009' || ccport == '019') {
                league1 = $('#drpCategor option:selected').val();
            }
            else {
                order = $('#drpCategor option:selected').val().toString();
            }

            if (ccport == '069') {
                Top_Player.loadTopPlyers();
            }
            else {
                Top_Player.GetTopPlayers(order, ccport, season1, league1);
            }
        });

        $('#tdQuarter').change(function () {
            if (ccport == '069') {
                Top_Player.loadTopPlyers();
            }
        });

        $('#tdRoutine').change(function () {
            if (ccport == '069') {
                Top_Player.loadTopPlyers();
            }
        });
    },

    //Call top players function 
    loadTopPlyers: function () {
        //sportId=072 is added to support the new sport - BOYS MPL for baseball
        if (ccport == '006' || ccport == "072" || ccport == '028' || ccport == '022' || ccport == '040' || ccport == '045' || ccport == '001' || ccport == '002' || ccport == '003' || ccport == '004' || ccport == '048' || ccport == '049' || ccport == '037' || ccport == '056' || ccport == '057' || ccport == '058' || ccport == '059' || ccport == '060' || ccport == '010' || ccport == '047' || ccport == '011' || ccport == '020' || ccport == '036' || ccport == '021' || ccport == '012' || ccport == "073" || ccport == "074" || ccport == "075" || ccport == "076" || ccport == "077" || ccport == '044' || ccport == '053' || ccport == '063' || ccport == '014' || ccport == '024' || ccport == '065' || ccport == '066' || ccport == '071' || ccport == '067' || ccport == '068' || ccport == '016' || ccport == '026' || ccport == '038' || ccport == '051' || ccport == '007' || ccport == '018' || ccport == '050' || ccport == '013' || ccport == '023' || ccport == '090' || ccport == '091') {
            league1 = 0;
            order = $('#drpCategor option:selected').val();
        }
        else
            if (ccport == '009' || ccport == '019' || ccport == '013' || ccport == '023') {
                order = $('#drpLeague option:selected').val();
            }
            else if (ccport == '030' || ccport == '031' || ccport == '078' || ccport == '079' || ccport == '032' || ccport == '033' || ccport == '034' || ccport == '035' || ccport == '070') {

            }
            else {
                league1 = $('#drpLeague option:selected').val();
                order = $('#drpCategor option:selected').val();
                if (ccport == '005' || ccport == '027' || ccport == '061')
                    order = 21;
                else if (ccport == '069') {
                    quarter = $('#drpQuarter option:selected').val();
                    routine = $('#drpRoutine option:selected').val();
                }
            }

        season1 = $('#drpSeason option:selected').val();

        if (ccport == '069') {
            if (league1 && order) {
                Top_Player.GetTopPlayersStunt(order, ccport, season1, league1, quarter, routine);
            }
        }
        else if (ccport != '009' || ccport != '019' || ccport != '013' || ccport != '023' || ccport != '030' || ccport != '031' || ccport != '078' || ccport != '079' || ccport != '032' || ccport != '033' || ccport != '034' || ccport != '035' || ccport != '070')
            Top_Player.GetTopPlayers(order, ccport, season1, league1);

        Top_Player.updateTopNav();

        //        var strSps = '033,034,032,035,030,031,078,079, 057,058,059,060';
        //        if (strSps.indexOf(ccport) > -1) {
        //            $('#std').css('display', 'none');
        //            $('#plf').css('display', 'none');
        //        }
        //        else {
        //            $('#std').css('display', 'block');
        //            $('#plf').css('display', 'block');
        //        }

        var strSps = '033,034,032,035,070,030,031,078,079,057';
        if (strSps.indexOf(ccport) > -1) {
            $('#std').css('display', 'none');
        }
        else {
            $('#std').css('display', 'block');
        }

        strSps = '033,034,032,035,070,030,031,078,079,009,019,057,058,059,060';
        if (strSps.indexOf(ccport) > -1) {
            $('#plf').css('display', 'none');
        }
        else {
            $('#plf').css('display', 'block');
        }


    },

    //Call sport specific top player function
    GetTopPlayers: function (order, sportcode, season, league) {
        var str1;
        var ajaxRequest;
        if (ajaxRequest != null) {
            ajaxRequest.abort();
        }

        $('#imgProgressBar').css('display', 'block');

        if (sportcode == '001' || sportcode == '002' || sportcode == '003' || sportcode == '004' || sportcode == '048' || sportcode == '049' || sportcode == '090' || sportcode == '091') {
            Top_Player_Basketball.GetTopPlayers(order, sportcode, season, league);
        }
        //sportId=072 is added to support the new sport - BOYS MPL for baseball
        else if (sportcode == '006' || sportcode == "072" || sportcode == '028' || sportcode == '022' || sportcode == '040' || sportcode == '045') {
            Top_Player_Base_Soft_ball.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '007' || sportcode == '018' || sportcode == '050') {
            Top_Player_Bowling.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '010' || sportcode == '047') {
            Top_Player_Golf.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '011' || sportcode == '020') {
            Top_Player_Handball.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '012' || sportcode == '021' || sportcode == "073" || sportcode == "074" || sportcode == "075" || sportcode == "076" || sportcode == "077") {
            Top_Player_Soccer.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '013' || sportcode == '023') {
            Top_Player_Swimming.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '014' || sportcode == '024') {
            Top_Player_Tennis.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '065' || sportcode == '066' || sportcode == '071') {
            Top_Player_Table_Tennis.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '067' || sportcode == '068') {
            Top_Player_Badminton.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '016' || sportcode == '026' || sportcode == '038' || sportcode == '051') {
            Top_Player_Volleyball.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '036' || sportcode == '044' || sportcode == '053' || sportcode == '063') {
            Top_Player_Lacrosse.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '037') {
            Top_Player_Crew.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '056') {
            Top_Player_Cricket.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '057') {
            Top_Player_DoubleDutch.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '058' || sportcode == '059' || sportcode == '060') {
            Top_Player_Rugby.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '061') {
            Top_Player_FlagFootball.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '008' || sportcode == '054' || sportcode == '055') {
            Top_Player_Fencing.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '005' || sportcode == '027') {

            Top_Player_Football.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '017' || sportcode == '064') {
            Top_Player_Wrestling.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '009' || sportcode == '019') {
            Top_Player_Gymnastics.GetTopPlayers(order, sportcode, season, league);
        }
        else if (sportcode == '030' || sportcode == '031' || sportcode == '078' || sportcode == '079' || sportcode == '032' || sportcode == '033' || sportcode == '034' || sportcode == '035' || sportcode == '070') {
            Top_Player_Track.GetTopPlayers(order, sportcode, season, league);
        }
    },

    GetTopPlayersStunt: function (order, sportcode, season, league, quarter, routine) {
        var str1;
        var ajaxRequest;
        if (ajaxRequest != null) {
            ajaxRequest.abort();
        }
        $('#imgProgressBar').css('display', 'block');

        if (sportcode == '069') {
            Top_Player_Stunt.GetTopPlayers(order, sportcode, season, league, quarter, routine);
        }
    },


    // On Sport selection in tabs call this reLoadData function
    reLoadData: function (spid, obj) {
        ccport = spid;
        $('div.standings-holder ul.tab-set li a').removeClass('active');
        $(obj).addClass('active');
        Top_Player.updateTopNav();
        Top_Player.TopPlayerFilter(ccport, season1);
        //sportId=072 is added to support the new sport - BOYS MPL for baseball
        if (ccport == '006' || ccport == "072" || ccport == '028' || ccport == '022' || ccport == '040' || ccport == '045' || ccport == '001' || ccport == '002' || ccport == '003' || ccport == '004' || ccport == '048' || ccport == '049' || ccport == '037' || ccport == '056' || ccport == '057' || ccport == '058' || ccport == '059' || ccport == '060' || ccport == '010' || ccport == '047' || ccport == '011' || ccport == '020' || ccport == '036' || ccport == '021' || ccport == '012' || ccport == "073" || ccport == "074" || ccport == "075" || ccport == "076" || ccport == "077" || ccport == '044' || ccport == '053' || ccport == '063' || ccport == '014' || ccport == '024' || ccport == '065' || ccport == '066' || ccport == '071' || ccport == '067' || ccport == '068' || ccport == '016' || ccport == '026' || ccport == '038' || ccport == '051' || ccport == '007' || ccport == '018' || ccport == '050' || ccport == '013' || ccport == '023' || ccport == '090' || ccport == '091') {
            league1 = 0;
            order = $('#drpCategor option:selected').val();
        }
        else
            if (ccport == '009' || ccport == '019' || ccport == '013' || ccport == '023') {
                order = $('#drpLeague option:selected').val();
            }
            else if (ccport == '030' || ccport == '031' || ccport == '078' || ccport == '079' || ccport == '032' || ccport == '033' || ccport == '034' || ccport == '035' || ccport == '070') {

            }
            else {
                league1 = $('#drpLeague option:selected').val();
                order = $('#drpCategor option:selected').val();
                if (ccport == '005' || sportcode == '061')
                    order = 21;
            }

        season1 = $('#drpSeason option:selected').val();
        Top_Player.GetTopPlayers(order, ccport, season1, league1);
    },


    //Bind divisions dropdown for football sport
    bindDivisionForSports: function (sportcode, season) {

        // modified football varsity with division to be database driven for 2023 and future years
        if (ccport == "005" || ccport == "027") {
            if (season < 2023) {
                $('#drpLeague').empty();
                var FootballVarsityOptions = {

                    1494: 'Highly Competitive',
                    1493: 'Most Competitive',
                    1217: 'Competitive'
                };

                var FootballVarsitySelect = $('#drpLeague');
                $.each(FootballVarsityOptions, function (val, text) {
                    FootballVarsitySelect.append(
                        $('<option></option>').val(val).html(text)
                    );
                });
            }

            else {
                Top_Player.bindLeagueForSport(ccport, season1);
            }
        }
        // end logic -modified football varsity with division to be database driven for 2023 and next future years      
    },

    //bind league dropdown from database 
    bindLeagueForSport: function (sportcode, season) {

        var ajaxRequest;
        if (ajaxRequest != null) {
            ajaxRequest.abort();
        }
        ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetSportLeague?csports='" + sportcode + "' &season='" + season + "'", null,
            function (data) {
                var strLeg = new Sys.StringBuilder("");
                //sportId=072 is added to support the new sport - BOYS MPL for baseball
                if (sportcode == '022') {
                    strLeg.append("<option value='0' >All Divisions</option>");
                    strLeg.append("<option value='AA' >All AA Divisions</option>");
                    strLeg.append("<option value='A' >All A Divisions</option>");
                    strLeg.append("<option value='B' >All B Divisions</option>");
                    strLeg.append("<option value='C' >All C Divisions</option>");
                }
                else if (sportcode == '028' || sportcode == '040' || sportcode == '045' || sportcode == "072") {
                    strLeg.append("<option value='0' >All Divisions</option>");
                    strLeg.append("<option value='A' >All A Divisions</option>");
                }
                else if ((sportcode == '006') && season >= 2015) {
                    strLeg.append("<option value='0' >All Divisions</option>");
                    strLeg.append("<option value='1A' >All 1A Divisions</option>");
                    strLeg.append("<option value='2A' >All 2A Divisions</option>");
                    strLeg.append("<option value='3A' >All 3A Divisions</option>");
                }
                else if (sportcode == '006' && season < 2015) {
                    strLeg.append("<option value='0' >All Divisions</option>");
                    strLeg.append("<option value='A' >All A Divisions</option>");
                    strLeg.append("<option value='B' >All B Divisions</option>");
                }

                else
                    strLeg.append("<option value='0' >All Divisions</option>");


                $.each(data.d, function (i, league) {
                    strLeg.append("<option value=" + league.lcode + " >" + league.clname + "</option>");
                });

                $('#drpLeague').html(strLeg.toString());
                $("#drpLeague > option").each(function () {
                    if (league1 == this.value) {
                        $('#drpLeague').val(league1);
                        return false;
                    }
                });
                league1 = $('#drpLeague').val();

                if (sportcode == '069') {
                    Top_Player.loadTopPlyers();
                }

            });
    },

    //Bind category dropdown from database 
    bindCategoryForSport: function (sportcode, season) {
        var ajaxRequest;
        if (ajaxRequest != null) {
            ajaxRequest.abort();
        }
        ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetSportEvent?csports='" + sportcode + "' &season='" + season + "'", null,
            function (data) {
                var strCat = new Sys.StringBuilder("");
                $.each(data.d, function (i, event) {
                    strCat.append("<option value=" + event.eventno + ">" + event.name + "</option>");
                    if (i == 0 && (sportcode == '013' || sportcode == '023'))
                        order = event.eventno;
                    else if (i == 0)
                        league1 = event.eventno;
                });
                if (sportcode == '009' || sportcode == '019') {
                    strCat.append("<option value=0>All Around</option>");
                }
                $('#drpCategor').html(strCat.toString());

                if (sportcode != '013' && sportcode != '023' && sportcode != '009' && sportcode != '019')
                    Top_Player.afterCallBack();
                else if (sportcode == '069') {
                    Top_Player.loadTopPlyers();
                }
                else
                    Top_Player.GetTopPlayers(order, sportcode, season1, league1);
            });
    },

    afterCallBack: function () {
        $('#drpCategor').change(function () {
            if (ccport == '030' || ccport == '031' || ccport == '078' || ccport == '079' || ccport == '032' || ccport == '033' || ccport == '034' || ccport == '035' || ccport == '070') {
                var orleg = $('#drpCategor option:selected').val().toString().split("#");
                order = orleg[0];
                league1 = orleg[1];
            }
            else if (ccport == '009' || ccport == '019') {
                league1 = $('#drpCategor option:selected').val();
            }
            else {
                order = $('#drpCategor option:selected').val().toString();
            }
            Top_Player.GetTopPlayers(order, ccport, season1, league1);
        });


    },


    //For track only - On league selection
    drpLeagueSel: function () {
        var ajaxRequest;
        if (ajaxRequest != null) {
            ajaxRequest.abort();
        }
        ccport = $('#drpLeague1 option:selected').val();
        spname = $('#drpLeague1 option:selected').html();
        season1 = $('#drpSeason1 option:selected').val();
        var urls = window.location.href;
        var url = urls.split('#')[0];
        window.location.replace(url + "#" + ccport + "/" + spname);
        Top_Player.updateTopNav();
        if (ccport == '030' || ccport == '031' || ccport == '078' || ccport == '079' || ccport == '032' || ccport == '033' || ccport == '034' || ccport == '035' || ccport == '070') {
            var strCat = new Sys.StringBuilder("");
            ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetSportEvmtDive?csports='" + ccport + "'&season='" + season1 + "'&typevar='EVENT'", null,
                function (data) {
                    strCat.append("<select id='drpCategor1' onchange='Top_Player.drpCategorySel();'>");
                    $.each(data.d, function (i, event) {
                        strCat.append("<option value=" + event.eventno + "#" + event.mtype + " >" + event.name + "</option>");
                        if (i == 0) {
                            order = event.eventno;
                            league1 = event.mtype;
                        }
                    });
                    strCat.append("</select>");
                    $('#tdCategor').html(strCat.toString());
                    $('#topHead').html("Top Player For " + spname);
                    Top_Player.GetTopPlayers(order, ccport, season1, league1);
                });
        }
    },

    //For track only - On Season selection
    drpSessionSel: function () {
        var ajaxRequest;
        if (ajaxRequest != null) {
            ajaxRequest.abort();
        }
        season1 = $('#drpSeason1 option:selected').val();
        if (ccport == '030' || ccport == '031' || ccport == '078' || ccport == '079' || ccport == '032' || ccport == '033' || ccport == '034' || ccport == '035' || ccport == '070') {
            var strCat = new Sys.StringBuilder("");
            ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetSportEvmtDive?csports='" + ccport + "'&season='" + season1 + "'&typevar='EVENT'", null,
                function (data) {
                    strCat.append("<select id='drpCategor1' onchange='Top_Player.drpCategorySel();'>");
                    $.each(data.d, function (i, event) {
                        strCat.append("<option value=" + event.eventno + "#" + event.mtype + " >" + event.name + "</option>");
                        if (i == 0) {
                            order = event.eventno;
                            league1 = event.mtype;
                        }
                    });
                    strCat.append("</select>");
                    $('#tdCategor').html(strCat.toString());
                });
        }
        Top_Player.GetTopPlayers(order, ccport, season1, league1);
    },


    //For track only - On Category selection
    drpCategorySel: function () {
        var orleg = $('#drpCategor1 option:selected').val().toString().split("#");
        order = orleg[0];
        league1 = orleg[1];
        season1 = $('#drpSeason1 option:selected').val();
        Top_Player.GetTopPlayers(order, ccport, season1, league1);
    },

    //Update navigation links, schedule, top players, rules and regulation etc.
    updateTopNav: function () {
        $('#topPlayersNav li a').each(function (i) {
            $(this).attr('href', $(this).attr('href').split('#')[0] + "#" + ccport + "/" + spname)
        });
    },

    //Bind category dropdown from database 
    bindCategory: function (sportcode, season) {
        var ajaxRequest;
        if (ajaxRequest != null) {
            ajaxRequest.abort();
        }
        ajaxRequest = $.getJSON(WEB_SERVICE_URL + "/GetSportStatisticalCategories?csports='" + sportcode + "'", null,
            function (data) {
                var strCat = new Sys.StringBuilder("");
                var header = null;

                $.each(data.d, function (i, event) {

                    if (event.header === null) {
                        strCat.append("<option value=" + event.id + ">" + event.name + "</option>");
                    }
                    else if (event.header !== header) {
                        strCat.append("<option value='00'>" + event.header + "</option>");
                        strCat.append("<option value=" + event.id + ">" + "&nbsp;&nbsp;&nbsp;" + event.name + "</option>");
                    }
                    else {
                        strCat.append("<option value=" + event.id + ">" + "&nbsp;&nbsp;&nbsp;" + event.name + "</option>");
                    }

                    if (i == 0) {
                        order = event.id;
                    }
                    header = event.header;
                });

                league1 = $('#drpLeague option:selected').val();
                if (league1 === undefined) {
                    league1 = 0;
                }

                $('#drpCategor').html(strCat.toString());

                if (sportcode == '057') {
                    $('#drpCategor').val(1);
                }
                else if (sportcode == '005' || sportcode == '027' || sportcode == '061') {
                    $('#drpCategor').val(21);
                }

                if (sportcode == '069') {
                    Top_Player.loadTopPlyers();
                }
                else {
                    Top_Player.GetTopPlayers(order, sportcode, season, league1);
                }
            });
    }

}