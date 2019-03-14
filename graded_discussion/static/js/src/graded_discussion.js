/* Javascript for GradedDiscussionXBlock. */
function GradedDiscussionXBlock(runtime, element) {

    function renderContributions(data){
        $(".list-contribution").empty();
        data.forEach(function(entry) {
            if ( entry.kind === "thread"){
                $(".list-contribution").append(createContributionElement("thread", entry.contribution, entry.parent, entry.created_at));
            } else {
                $(".list-contribution").append(createContributionElement("comment", entry.contribution, entry.parent, entry.created_at));
            }
        });
        updateDateTime();
        $(".grading-section .grade-section").show();
    };


    function createContributionElement(kind, contribution, parent, createdAt){
        var element = $("<li></li>");
        var div = $('<div class="'+kind+'-contribution"></div>');
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
        $(".date-time").each(function() {
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

    function getContributions(users){
        $.ajax({
            type: "POST",
            url: reloadPage,
            data: JSON.stringify({"users": users}),
            success: function(data){
                $(".grading-pop-up .users-list li").each(function(){
                    var username = $(this).attr("username");
                    $(this).attr("contributions", data[username]);
                    if ($(this).hasClass("active")) {
                        renderContributions(JSON.parse($(this).attr("contributions")));
                    }
                })

            },
        });
    }

    function submit(){
        var score = $("#grade").val();
        var comment = $("#comment").val();
        var username = $(".grading-pop-up .users-list .active").attr("username");
        if (username == null ){
            alert("Select a user");
        } else {
            $.ajax({
                type: "GET",
                url: enterGrade,
                data: {"user": username, "score": score, "comment": comment},
                success: function (){
                    $(".active").remove();
                    $(".list-contribution").empty();
                    if($(".users-list li").length ==0){
                        $(".staff-section .users-list").append("<p>No available users to grade</p>");
                    }
                },
            }).fail(function(data){
                alert(data.responseJSON.error);
            })
        }
        $("#grade").val("");
        $("#comment").val("");
    }

    $(function ($) {
        /* Here's where you'd do things on page load. */
    });

    var reloadPage = runtime.handlerUrl(element, "get_contributions");
    var enterGrade = runtime.handlerUrl(element, "enter_grade");

    updateDateTime();

    $(".grading-pop-up .reload-button").click(function(){
        var users = [];
        $(".grading-pop-up .users-list li").each(function(){
            users.push($(this).attr("username"));
        })
        getContributions(users);
    })

    $(".grading-pop-up .oldest").click(function(){
        $(".users-list li").sort(sortByOldest).appendTo('.users-list');
    });

    $(".grading-pop-up .newest").click(function(){
        $(".users-list li").sort(sortByNewest).appendTo('.users-list');
    });

    $(".grading-pop-up .users-list li").click(function(){
        var username = $(this).attr("username");
        var contributions = JSON.parse($(this).attr("contributions"));
        $("li").removeClass("active");
        $(this).addClass("active");
        renderContributions(contributions);
    });

    $(".graded_discussion_block #grade-button").click(function(){
        $(".grading-pop-up").modal({
          fadeDuration: 100
        });
    });

    $(".grading-pop-up #submit-button").click(function(){
        submit();
    });

    $(".grading-pop-up .staff-section .menu-icon").click(function(){
        $(".grading-pop-up .staff-section .filters").fadeIn("slow");
        $(".grading-pop-up .staff-section form").hide();
        $(this).hide();
    });

    $(".grading-pop-up .staff-section .filters .close-button").click(function(){
        $(".grading-pop-up .staff-section .filters").hide();
        $(".grading-pop-up .staff-section .menu-icon").fadeIn("slow");
        $(".grading-pop-up .staff-section form").fadeIn("slow");
    });

    $(".grading-pop-up .search-input").on("keyup", function() {
        var value = $(this).val().toLowerCase();
        $(".student-list-section .item").filter(function() {
          $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    $(".users-list li").sort(sortByOldest).appendTo('.users-list');

    $('.grading-pop-up li :checkbox').change(function() {
        var validIds = [];
        $('.grading-pop-up li :checkbox:checked').each(function() {
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
