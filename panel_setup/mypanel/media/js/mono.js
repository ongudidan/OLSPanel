/**
 * WEBSITE: https://themefisher.com
 * TWITTER: https://twitter.com/themefisher
 * FACEBOOK: https://www.facebook.com/themefisher
 * GITHUB: https://github.com/themefisher/
 */

/* ====== Index ======

1. SCROLLBAR SIDEBAR
2. MOBILE OVERLAY
3. SIDEBAR MENU
4. SIDEBAR TOGGLE FOR MOBILE
5. SIDEBAR TOGGLE FOR VARIOUS SIDEBAR LAYOUT
6. TODO LIST
7. RIGHT SIDEBAR
8. OFFCANVAS
9. DROPDOWN NOTIFY
10. REFRESS BUTTON
11. NAVBAR TRANSPARENT SCROLL
12. NAVBAR SEARCH
====== End ======*/

$(document).ready(function () {
  "use strict";

  /*======== 1. SCROLLBAR SIDEBAR ========*/

  /*======== 2. MOBILE OVERLAY ========*/
  if ($(window).width() < 768) {
    $(".sidebar-toggle").on("click", function () {
      $("body").css("overflow", "hidden");
      $("body").prepend('<div class="mobile-sticky-body-overlay"></div>');
    });

    $(document).on("click", ".mobile-sticky-body-overlay", function (e) {
      $(this).remove();
      $("#body")
        .removeClass("sidebar-mobile-in")
        .addClass("sidebar-mobile-out");
      $("body").css("overflow", "auto");
    });
  }

  /*======== 3. SIDEBAR MENU ========*/
  $(".sidebar .nav > .has-sub > a").click(function () {
    $(this).parent().siblings().removeClass("expand");
    $(this).parent().toggleClass("expand");
  });

  $(".sidebar .nav > .has-sub .has-sub > a").click(function () {
    $(this).parent().toggleClass("expand");
  });

  /*======== 4. SIDEBAR TOGGLE FOR MOBILE ========*/
  if ($(window).width() < 768) {
       body = "#body";
     $(body).removeClass("sidebar-mobile-in").addClass("sidebar-mobile-out");
      
    $(document).on("click", ".sidebar-toggle", function (e) {
      e.preventDefault();
      var min = "sidebar-mobile-in",
        min_out = "sidebar-mobile-out",
        body = "#body";
      $(body).hasClass(min)
        ? $(body).removeClass(min).addClass(min_out)
        : $(body).addClass(min).removeClass(min_out);
    });
  }

  /*======== 5. SIDEBAR TOGGLE FOR VARIOUS SIDEBAR LAYOUT ========*/
  var body = $("#body");
  if ($(window).width() >= 768) {
    if (body.hasClass("sidebar-mobile-in sidebar-mobile-out")) {
      body.removeClass("sidebar-mobile-in sidebar-mobile-out");
    }
 body.removeClass("sidebar-collapse sidebar-minified-out")
            .addClass("sidebar-minified");
          window.isMinified = true;
          window.isCollapsed = false;

    $("#sidebar-toggler").on("click", function () {
      if (
        body.hasClass("sidebar-fixed-offcanvas") ||
        body.hasClass("sidebar-static-offcanvas")
      ) {
        $(this)
          .addClass("sidebar-offcanvas-toggle")
          .removeClass("sidebar-toggle");
        if (window.isCollapsed === false) {
          body.addClass("sidebar-collapse");
          window.isCollapsed = true;
          window.isMinified = false;
        } else {
          body.removeClass("sidebar-collapse");
          body.addClass("sidebar-collapse-out");
          setTimeout(function () {
            body.removeClass("sidebar-collapse-out");
          }, 300);
          window.isCollapsed = false;
        }
      }

      if (body.hasClass("sidebar-fixed") || body.hasClass("sidebar-static")) {
        $(this)
          .addClass("sidebar-toggle")
          .removeClass("sidebar-offcanvas-toggle");
        if (window.isMinified === false) {
          body
            .removeClass("sidebar-collapse sidebar-minified-out")
            .addClass("sidebar-minified");
          window.isMinified = true;
          window.isCollapsed = false;
        } else {
          body.removeClass("sidebar-minified");
          body.addClass("sidebar-minified-out");
          window.isMinified = false;
        }
      }
    });
  }

  if ($(window).width() >= 1440 && $(window).width() < 992) {
    if (body.hasClass("sidebar-fixed") || body.hasClass("sidebar-static")) {
      body
        .removeClass("sidebar-collapse sidebar-minified-out")
        .addClass("sidebar-minified");
      window.isMinified = true;
    }
  }

});
