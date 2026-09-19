/*
 * additional data structure to store ip config into a data structure
 */

#ifndef KEY_IP
#define KEY_IP

/*
 * Access headers
 */

void key_ip_init();
int  key_ip_insert( int key, char *data );
int  key_ip_delete( int key );
int  key_ip_get   ( int key, char **data );
#endif