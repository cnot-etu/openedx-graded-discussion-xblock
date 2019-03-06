/* Javascript for GradedDiscussionXBlock. */
function GradedDiscussionXBlock(runtime, element) {

    function renderContributions(data){
        $(".list-contribution").empty();

        data.forEach(function(entry) {
            if ( entry.kind === "thread"){
                $(".list-contribution").append(createThreadElement(entry.contribution, entry.created_at));
            } else {
                $(".list-contribution").append(createCommentElement(entry.contribution, entry.parent, entry.created_at));
            }
        });
        updateDateTime();
        $(".grading-section .grade-section").show();
    };


    function createThreadElement(contribution, createdAt){
        var element = $("<li></li>");
        var div = $('<div class="thread-contribution"></div>');
        var contribution = $('<p>'+contribution+'</p>');
        var date = $('<span class="date-time" value="'+createdAt+'"></span>');

        contribution.appendTo(div);
        date.appendTo(div);
        div.appendTo(element);

        return element

    }

    function createCommentElement(contribution, parent, createdAt){
        var element = $("<li></li>");
        var div = $('<div class="comment-contribution"></div>');
        var contribution = $('<p>'+contribution+'</p>');
        var parent = $('<span class="parent-contribution">'+parent.name+' by '+parent.author+'</span>');
        var date = $('<span class="date-time" value="'+createdAt+'"></span>');

        contribution.appendTo(div);
        parent.appendTo(div);
        date.appendTo(div);
        div.appendTo(element);

        return element

    }

    function updateDateTime(){
        $(".graded_discussion_block .date-time").each(function() {
            var value = $(this).attr("value");
            if (value==""){
                $(this).text("This user has no contributions");
            } else {
                var date = new Date(value);
                $(this).text(date.toLocaleString());
            }

        });
    }

    function sortByOldest(a, b){
        var firstDate = $(a).find('span').attr("value");
        var secondDate = $(b).find('span').attr("value");

        if (firstDate == ""){
            return 1;
        } else if (secondDate == "") {
            return -1;
        }

        return (firstDate > secondDate) ? 1 : -1;
    }

    function sortByNewest(a, b){
        var firstDate = $(a).find('span').attr("value");
        var secondDate = $(b).find('span').attr("value");

        if (firstDate == ""){
            return 1;
        } else if (secondDate == "") {
            return -1;
        }

        return (firstDate < secondDate) ? 1 : -1;
    }

    function getContributions(username){
        $.ajax({
            type: "GET",
            url: reloadPage,
            data: {"user": username},
            success: renderContributions
        });
    }


    $(function ($) {
        /* Here's where you'd do things on page load. */
    });

    var reloadPage = runtime.handlerUrl(element, "refresh_data");
    var enterGrade = runtime.handlerUrl(element, "enter_grade");

    var grade = $("#grade");
    var comment = $("#comment");
    var allFields = $( [] ).add(grade).add(comment);

    var dialog = $( "#dialog-form" ).dialog({
      autoOpen: false,
      height: 400,
      width: 350,
      modal: true,
      buttons: {
        "Submit": function(){
            var score = $("#grade").val();
            var comment = $("#comment").val();
            var username = $(".graded_discussion_block .users-list .active").attr("username");
            if (username == null ){
                dialog.dialog("close");
                alert("Select a user");
            } else {
                $.ajax({
                    type: "GET",
                    url: enterGrade,
                    data: {"user": username, "score": score, "comment": comment},
                });
            }

        },
        Cancel: function() {
          dialog.dialog("close");
        }
      },
      close: function() {
        allFields.removeClass("ui-state-error");
      }
    });

    updateDateTime();

    $(".student-section .reload-button").click(function(){
        getContributions(null);
    })

    $(".graded_discussion_block .oldest").click(function(){
        $(".users-list li").sort(sortByOldest).appendTo('.users-list');
    });

    $(".graded_discussion_block .newest").click(function(){
        $(".users-list li").sort(sortByNewest).appendTo('.users-list');
    });

    $(".graded_discussion_block .users-list li").click(function(){
        var username = $(this).attr("username");
        $("li").removeClass("active");
        $(this).addClass("active");
        getContributions(username);
    });

    $(".graded_discussion_block #grade-button").click(function(){
        dialog.dialog( "open" );
    });

    $(".graded_discussion_block .staff-section .menu-icon").click(function(){
        $(".graded_discussion_block .staff-section .filters").fadeIn("slow");
        $(this).hide();
    });

    $(".graded_discussion_block .staff-section .filters .close-button").click(function(){
        $(".graded_discussion_block .staff-section .filters").hide();
        $(".graded_discussion_block .staff-section .menu-icon").fadeIn("slow");
    });

    $(".graded_discussion_block .search-input").on("keyup", function() {
        var value = $(this).val().toLowerCase();
        $(".student-list-section .item").filter(function() {
          $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    $(".users-list li").sort(sortByOldest).appendTo('.users-list');

    $('.graded_discussion_block li :checkbox').change(function() {
        var validIds = [];
        $('.graded_discussion_block li :checkbox:checked').each(function() {
            validIds.push($(this).attr("id"));
        });
        if (validIds.length == 0) {
            $(".student-list-section .item").filter(function() {
                $(this).toggle(true);
            });
        } else {
            $(".student-list-section .item").filter(function() {
                $(this).toggle(validIds.includes($(this).attr("team-id")) || validIds.includes($(this).attr("cohort-id")));
            });
        }

    });

}
