# footer.pl

sub print_footer {
    my () = @_;

   print <<"END_HTML";

<br>

</body>
</html>


END_HTML

    print $content_html;
}
1;